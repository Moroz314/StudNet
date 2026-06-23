import { useState, useRef, useEffect } from "react";
import {
  FaFilePdf,
  FaFileImage,
  FaFileCode,
  FaFileArchive,
  FaFileWord,
  FaFileExcel,
  FaFile,
  FaDownload,
  FaEllipsisV,
  FaTrash,
} from "react-icons/fa";

/**
 * FileCard — карточка файла проекта.
 * Поддерживает:
 * 1) Объект file (ProjectFileResponse из API S3): { id, original_filename, file_type, mime_type, size_bytes, uploaded_at, uploaded_by, ... }
 * 2) Legacy props: name, type, size, uploadDate, uploadedBy
 */
export const FileCard = ({
  file,
  name,
  type,
  size,
  uploadDate,
  uploadedBy,
  onDownload,
  onDelete,
  onMenuClick,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const displayName = file?.original_filename ?? name ?? "Файл";
  const displayType = file?.file_type ?? type ?? file?.mime_type?.split("/")[0];
  const displaySize = file?.size_bytes ?? (typeof size === "number" ? size : parseSize(size));
  const displayDate = file?.uploaded_at
    ? formatDate(file.uploaded_at)
    : uploadDate ?? "Сегодня";
  const displayUploadedBy = file?.uploaded_by ?? uploadedBy;

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getFileIcon = () => {
    const extension = displayName.split(".").pop()?.toLowerCase();

    switch (displayType || extension) {
      case "pdf":
        return <FaFilePdf className="text-red-400" />;
      case "jpg":
      case "jpeg":
      case "png":
      case "gif":
      case "svg":
      case "image":
        return <FaFileImage className="text-green-400" />;
      case "js":
      case "jsx":
      case "ts":
      case "tsx":
      case "html":
      case "css":
      case "py":
      case "java":
      case "code":
        return <FaFileCode className="text-blue-400" />;
      case "zip":
      case "rar":
      case "7z":
      case "tar":
      case "archive":
        return <FaFileArchive className="text-yellow-400" />;
      case "doc":
      case "docx":
      case "word":
        return <FaFileWord className="text-blue-500" />;
      case "xls":
      case "xlsx":
      case "excel":
        return <FaFileExcel className="text-green-500" />;
      default:
        return <FaFile className="text-gray-400" />;
    }
  };

  const handleMenuToggle = (e) => {
    e.stopPropagation();
    if (onMenuClick) {
      onMenuClick(file ?? { name: displayName });
    } else {
      setMenuOpen((prev) => !prev);
    }
  };

  const handleDownload = (e) => {
    e.stopPropagation();
    setMenuOpen(false);
    onDownload?.(file ?? { name: displayName });
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    setMenuOpen(false);
    onDelete?.(file);
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 hover:border-purple-500/50 transition-all duration-300 group relative">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="text-2xl">{getFileIcon()}</div>
          <div className="flex-1 min-w-0">
            <h4 className="text-white font-medium truncate text-sm" title={displayName}>
              {displayName}
            </h4>
            <p className="text-gray-400 text-xs">
              {formatSize(displaySize)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {(onDownload || file) && (
            <button
              onClick={handleDownload}
              className="text-gray-400 hover:text-purple-400 transition-colors p-1"
              title="Скачать"
            >
              <FaDownload size={14} />
            </button>
          )}
          <div className="relative" ref={menuRef}>
            <button
              onClick={handleMenuToggle}
              className="text-gray-400 hover:text-purple-400 transition-colors p-1"
              title="Действия"
            >
              <FaEllipsisV size={14} />
            </button>
            {menuOpen && !onMenuClick && (
              <div className="absolute right-0 top-full mt-1 py-1 w-40 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-10">
                {(onDownload || file) && (
                  <button
                    onClick={handleDownload}
                    className="w-full px-3 py-2 text-left text-sm text-gray-200 hover:bg-gray-700 flex items-center gap-2"
                  >
                    <FaDownload size={12} />
                    Скачать
                  </button>
                )}
                {onDelete && file && (
                  <button
                    onClick={handleDelete}
                    className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-gray-700 flex items-center gap-2"
                  >
                    <FaTrash size={12} />
                    Удалить
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{displayDate}</span>
        {displayUploadedBy && (
          <span className="truncate max-w-24" title={String(displayUploadedBy)}>
            {displayUploadedBy}
          </span>
        )}
      </div>
    </div>
  );
};

function formatSize(bytes) {
  if (bytes == null || isNaN(bytes)) return "—";
  const n = Number(bytes);
  if (n === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(n) / Math.log(k));
  return parseFloat((n / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  const today = new Date();
  const isToday =
    d.getDate() === today.getDate() &&
    d.getMonth() === today.getMonth() &&
    d.getFullYear() === today.getFullYear();
  return isToday ? "Сегодня" : d.toLocaleDateString("ru-RU");
}

function parseSize(val) {
  if (val == null) return 0;
  if (typeof val === "number" && !isNaN(val)) return val;
  const str = String(val).trim();
  const num = parseFloat(str);
  if (str.includes("GB") || str.toLowerCase().includes("gb")) return num * 1024 * 1024 * 1024;
  if (str.includes("MB") || str.toLowerCase().includes("mb")) return num * 1024 * 1024;
  if (str.includes("KB") || str.toLowerCase().includes("kb")) return num * 1024;
  return isNaN(num) ? 0 : num;
}
