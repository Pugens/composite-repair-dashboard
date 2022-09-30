import copy
import numpy as np
import open3d as o3d


def load_ply(path):
    """Loads a ply file and returns a point cloud

    Args:
        path (str): path to ply file

    Returns:
        pcd: point cloud
    """
    pcd = o3d.io.read_point_cloud(path)
    return pcd


def load_mesh(path):
    """Loads a mesh file and returns a mesh

    Args:
        path (str): path to mesh file

    Returns:
        mesh: mesh
    """
    mesh = o3d.io.read_triangle_mesh(path)
    mesh.compute_vertex_normals()
    mesh.paint_uniform_color([0.5, 0.5, 0.5])
    return mesh


def estimate_normals(pcd, voxel_size, max_nn=30):
    """Estimate normals for a point cloud

    Args:
        pcd (pcd): point cloud
        voxel_size (float): voxel size
    Returns:
        pcd: point cloud with normals
    """
    pcd.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=max_nn)
    )
    return pcd


def draw_registration_result(source, target, transformation):

    return


def draw_registration_result(source, target, transformation):
    """Draws 2 point clouds in the source refeernce frame, while applying the transformation to the target point cloud

    Args:
        source (_type_): Origianl point cloud
        target (_type_): Origianl point cloud
        transformation (_type_): Transformation matrix
    """

    # Since the functions transform and paint_uniform_color change the point cloud,
    # we call copy.deepcopy to make copies and protect the original point clouds.
    source_temp = copy.deepcopy(source)
    target_temp = copy.deepcopy(target)
    source_temp.paint_uniform_color([1, 0, 0])
    target_temp.paint_uniform_color([0, 0, 1])
    source_temp.transform(transformation)
    o3d.visualization.draw_geometries(
        [source_temp, target_temp],
        # settings for 3D viewport intial camera position, avoid if using any other mesh than DemoICPPointClouds
        # zoom=0.4559,
        # front=[0.6452, -0.3036, -0.7011],
        # lookat=[1.9892, 2.0208, 1.8945],
        # up=[-0.2779, -0.9482, 0.1556],
    )


def preprocess_point_cloud(pcd, voxel_size):
    """Downsample with a voxel size voxel_size

    Args:
        pcd (pcd): Origianl point cloud
        voxel_size (float): Downsample voxel size (change according to point cloud overall size)

    Returns:
        pcd: Returns downsampled point cloud and FPFH features
    """

    # print(":: Downsample with a voxel size %.3f." % voxel_size)
    pcd_down = pcd.voxel_down_sample(voxel_size)

    radius_normal = voxel_size * 2
    # print(":: Estimate normal with search radius %.3f." % radius_normal)
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30)
    )

    radius_feature = voxel_size * 5
    # print(":: Compute FPFH feature with search radius %.3f." % radius_feature)
    pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=100),
    )
    return pcd_down, pcd_fpfh


def prepare_dataset(voxel_size, path1, path2, source_scale=1, target_scale=1):
    source = o3d.io.read_point_cloud(path1)
    target = o3d.io.read_point_cloud(path2)
    if source_scale != 1:
        source.scale(source_scale, center=source.get_center())
    if target_scale != 1:
        target.scale(target_scale, center=target.get_center())
    draw_registration_result(source, target, np.identity(4))

    print("   Then downsample the two point clouds.")
    source_down, source_fpfh = preprocess_point_cloud(source, voxel_size)
    target_down, target_fpfh = preprocess_point_cloud(target, voxel_size)
    return source, target, source_down, target_down, source_fpfh, target_fpfh


def display_inlier_outlier(cloud, ind):
    """Uses select_by_index, which takes a binary mask to output only the selected points. The selected points and the non-selected points are visualized.

    Args:
        cloud (_type_): point cloud
        ind (_type_): integer index of inliers
    """
    inlier_cloud = cloud.select_by_index(ind)
    outlier_cloud = cloud.select_by_index(ind, invert=True)

    print("Showing outliers (red) and inliers (gray): ")
    outlier_cloud.paint_uniform_color([1, 0, 0])
    inlier_cloud.paint_uniform_color([0.8, 0.8, 0.8])
    o3d.visualization.draw_geometries([inlier_cloud, outlier_cloud])


def global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size):
    distance_threshold = voxel_size * 1.5
    print(":: RANSAC registration on downsampled point clouds.")
    print("   Since the downsampling voxel size is %.3f," % voxel_size)
    print("   we use a liberal distance threshold %.3f." % distance_threshold)
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down,
        target_down,
        source_fpfh,
        target_fpfh,
        True,
        distance_threshold,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(True),
        3,
        [
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(
                distance_threshold
            ),
        ],
        o3d.pipelines.registration.RANSACConvergenceCriteria(100000, 0.999),
    )
    return result


def fast_global_registration(
    source_down, target_down, source_fpfh, target_fpfh, voxel_size
):
    distance_threshold = voxel_size * 0.5
    print(
        ":: Apply fast global registration with distance threshold %.3f"
        % distance_threshold
    )
    result = o3d.pipelines.registration.registration_fgr_based_on_feature_matching(
        source_down,
        target_down,
        source_fpfh,
        target_fpfh,
        o3d.pipelines.registration.FastGlobalRegistrationOption(
            maximum_correspondence_distance=distance_threshold
        ),
    )
    return result


def local_registration(source, target, distance_threshold, result_global):
    result = o3d.pipelines.registration.registration_icp(
        source,
        target,
        distance_threshold,
        result_global.transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(),
    )
    return result
