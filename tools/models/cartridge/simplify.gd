extends SceneTree

## 用引擎自带的 meshoptimizer 减面。只挑顶点、不挪顶点，平面还是平的。
## godot --headless --script simplify.gd -- <输入> <输出> <误差>
## 输入：int32 顶点数、int32 面数、float32 顶点、int32 面。输出：int32 面。误差是相对模型最长边的比例。


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var file := FileAccess.open(args[0], FileAccess.READ)
	var vertex_count := file.get_32()
	var face_count := file.get_32()
	var vertices := file.get_buffer(vertex_count * 12).to_float32_array()
	var faces := file.get_buffer(face_count * 12).to_int32_array()
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in vertex_count:
		tool.add_vertex(Vector3(vertices[i * 3], vertices[i * 3 + 1], vertices[i * 3 + 2]))
	for index in faces:
		tool.add_index(index)
	var kept := tool.generate_lod(float(args[2]), 3)
	FileAccess.open(args[1], FileAccess.WRITE).store_buffer(kept.to_byte_array())
	quit(0)
