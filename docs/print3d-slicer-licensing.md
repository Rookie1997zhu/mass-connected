# 3D 打印切片组件许可说明

## 本仓库提取代码

从 `3D-Printing-Quote-Engine-master`（Machine Shop Suite）提取的切片调用与
G-code 解析思路，原项目为 **MIT License**。移植时去掉了静默假数据兜底逻辑。

## PrusaSlicer（AGPL-3.0）

`slicer-worker` Docker 镜像内嵌 **PrusaSlicer**（AGPL-3.0）。

- 调用方式：独立 CLI 子进程（非链接进 Python）。
- **分发含 PrusaSlicer 的镜像时**，须遵守 AGPL：提供对应版本源码获取方式。
- 官方源码：https://github.com/prusa3d/PrusaSlicer

构建时请将固定版本的 `PrusaSlicer.AppImage`（Linux x86_64）置于
`backend/` 构建上下文，或通过 compose build args 指定路径。

## STEP 转换

STEP→STL 使用项目既有 **OpenCASCADE / cadquery-ocp**，不使用 gmsh 进程内调用。
