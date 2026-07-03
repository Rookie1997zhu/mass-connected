ALLOWED_ATTACHMENT_EXTENSIONS = {
    "pdf", "step", "stp", "igs", "iges", "dwg", "dxf", "x_t", "x_b",
    "sldprt", "stl", "3mf", "zip", "rar", "7z",
    "jpg", "jpeg", "png", "gif", "webp", "xlsx", "xls", "docx", "doc", "csv", "txt",
}
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024


def validate_upload_file(file_obj):
    if not file_obj:
        return "MEDIA_FILE_TYPE_INVALID", "请上传文件"
    ext = file_obj.name.rsplit(".", 1)[-1].lower() if "." in file_obj.name else ""
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        return "MEDIA_FILE_TYPE_INVALID", "不支持的文件类型"
    if file_obj.size > MAX_ATTACHMENT_SIZE:
        return "MEDIA_FILE_SIZE_EXCEEDED", "文件大小超限（最大 20MB）"
    return None, ext
