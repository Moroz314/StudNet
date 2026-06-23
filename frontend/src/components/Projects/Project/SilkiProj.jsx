import { FaGithub, FaTelegram, FaVk, FaInstagram, FaUniversity, FaBook, FaCode, FaExternalLinkAlt, FaPlus } from "react-icons/fa";
import { FaChalkboard } from "react-icons/fa";

/** Карточка одной ссылки */
export const SilkiProj = ({ name, link }) => {
  
  function extractDomain(url) {
    try {
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
      }
      
      const urlObj = new URL(url);
      let domain = urlObj.hostname;
      domain = domain.replace(/^www\./, '');
      return domain;
    } catch (error) {
      return null;
    }
  }

  const getFileIcon = () => {
    const link_name = extractDomain(link);
    
    switch (link_name) {
      case 'miro.com':
        return (
          <div className="flex items-center gap-2">
            <FaChalkboard className="text-2xl text-yellow-400" />
            <span className="text-white font-medium">Miro</span>
          </div>
        );
      case 't.me':
        return (
          <div className="flex items-center gap-2">
            <FaTelegram className="text-2xl text-blue-400" />
            <span className="text-white font-medium">Telegram</span>
          </div>
        );
      case 'github.com':
        return (
          <div className="flex items-center gap-2">
            <FaGithub className="text-2xl text-gray-300" />
            <span className="text-white font-medium">GitHub</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-2">
            <FaBook className="text-2xl text-gray-400" />
            <span className="text-white font-medium">{link_name}</span>
          </div>
        );
    }
  };

  return (
    <a 
      href={link} 
      target="_blank" 
      rel="noopener noreferrer"
      className="block group mt-5"
    >
      <div className="bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700 rounded-2xl p-6 hover:border-purple-500/70 hover:shadow-2xl hover:shadow-purple-500/20 transition-all duration-300 transform hover:-translate-y-1">
        
        {/* Иконка и заголовок */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {getFileIcon()}
          </div>
          <FaExternalLinkAlt className="text-gray-400 group-hover:text-purple-400 transition-colors text-sm" />
        </div>

        {/* Название проекта */}
        <h4 className="text-white font-semibold text-lg mb-2 line-clamp-2">
          {name}
        </h4>

        {/* Ссылка */}
        <p className="text-gray-400 text-sm truncate group-hover:text-purple-300 transition-colors">
          {link}
        </p>
      </div>
    </a>
  );
};

function getDisplayNameFromUrl(url) {
  try {
    const u = url.startsWith("http") ? url : "https://" + url;
    const host = new URL(u).hostname.replace(/^www\./, "");
    return host;
  } catch {
    return url;
  }
}

/** Секция "Инструменты и ссылки" с кнопкой добавления (API: links = string[]) */
export const LinksSection = ({ links = [], onAddLink, onRemoveLink }) => {
  const normalizeLink = (item) => {
    if (typeof item === "string") return { name: getDisplayNameFromUrl(item), link: item };
    return {
      name: item?.name ?? item?.title ?? getDisplayNameFromUrl(item?.link || item?.url || ""),
      link: item?.link ?? item?.url ?? "",
    };
  };
  const items = links.map(normalizeLink).filter((l) => l.link);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold text-white">Инструменты и ссылки</h3>
        {onAddLink && (
          <button
            onClick={onAddLink}
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-sm transition-colors"
          >
            <FaPlus size={14} />
            Добавить ссылку
          </button>
        )}
      </div>
      {items.length > 0 ? (
        <div className="grid grid-cols-1 gap-3">
          {items.map((silk, index) => (
            <div key={index} className="relative group/card">
              <SilkiProj name={silk.name} link={silk.link} />
              {onRemoveLink && (
                <button
                  onClick={() => onRemoveLink(index)}
                  className="absolute top-2 right-2 p-2 rounded-lg bg-gray-800/90 text-gray-400 hover:text-red-400 opacity-0 group-hover/card:opacity-100 transition-opacity"
                  title="Удалить"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-sm">
          Ссылок пока нет. Нажмите «Добавить ссылку», чтобы добавить Miro, Figma и другие сервисы.
        </p>
      )}
    </div>
  );
};