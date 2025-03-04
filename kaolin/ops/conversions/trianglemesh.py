# Copyright (c) 2019,20-21 NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
from ..mesh.trianglemesh import _unbatched_subdivide_vertices
from .pointcloud import _base_points_to_voxelgrids

__all__ = ['trianglemeshes_to_voxelgrids']

def trianglemeshes_to_voxelgrids(vertices, faces, resolution, origin=None, scale=None,
                                 return_sparse=False):
    r"""Converts meshes to surface voxelgrids of a given resolution. It first upsamples 
    triangle mesh's vertices to given resolution, then it performs a box test. 
    If a voxel contains a triangle vertex, set that voxel to 1. Vertex will be 
    offset and scaled as following: 
    :math:`\text{normalized_vertices} = (\text{vertices} - \text{origin}) / \text{scale}`
    the voxelgrids will only be generated in the range [0, 1] of normalized_vertices.

    Args:
        vertices (torch.tensor): batched vertices of shape (B, V, 3) of mesh to convert.
        faces (torch.tensor): unbatched faces of shape (F, 3) of mesh to convert.
        resolution (int): desired resolution of generated voxelgrid.
        origin (torch.tensor): origin of the voxelgrid in the mesh coordinates. It has shape :math:`(\text{batch_size}, 3)`.
                               Default: origin = torch.min(vertices, dim=1)[0]
        scale (torch.tensor): the scale by which we divide the vertex position. It has shape :math:`(\text{batch_size})`.
                              Default: scale = torch.max(torch.max(vertices, dim=1)[0] - origin, dim=1)[0]

    Returns:
        (torch.Tensor or torch.FloatTensor):
            Binary batched voxelgrids of shape (B, resolution, resolution, resolution).
            If return_sparse == True, sparse tensor is returned.

    Example:
        >>> vertices = torch.tensor([[[0, 0, 0],
        ...                           [1, 0, 0],
        ...                           [0, 0, 1]]], dtype=torch.float)
        >>> faces = torch.tensor([[0, 1, 2]], dtype=torch.long)
        >>> origin = torch.zeros((1, 3))
        >>> scale = torch.ones((1))
        >>> trianglemeshes_to_voxelgrids(vertices, faces, 3, origin, scale)
        tensor([[[[1., 1., 1.],
                  [0., 0., 0.],
                  [0., 0., 0.]],
        <BLANKLINE>
                 [[1., 1., 0.],
                  [0., 0., 0.],
                  [0., 0., 0.]],
        <BLANKLINE>
                 [[1., 0., 0.],
                  [0., 0., 0.],
                  [0., 0., 0.]]]])
    """
    vertices_dtype = vertices.dtype
    vertices_device = vertices.device

    if not isinstance(resolution, int):
        raise TypeError(f"Expected resolution to be int "
                        f"but got {type(resolution)}.")

    if origin is None:
        min_val = torch.min(vertices, dim=1)[0]
        origin = min_val

    if scale is None:
        max_val = torch.max(vertices, dim=1)[0]
        scale = torch.max(max_val - origin, dim=1)[0]

    batch_size = vertices.shape[0]
    voxelgrids = torch.zeros((batch_size, resolution, resolution, resolution), device=vertices_device, dtype=vertices_dtype)

    batched_points = (vertices - origin.unsqueeze(1)) / scale.view(-1, 1, 1)

    for i in range(batch_size):

        points = _unbatched_subdivide_vertices(batched_points[i], faces, resolution)

        voxelgrid = _base_points_to_voxelgrids(points.unsqueeze(0), resolution, return_sparse=return_sparse)

        voxelgrids[i] = voxelgrid

    return voxelgrids
