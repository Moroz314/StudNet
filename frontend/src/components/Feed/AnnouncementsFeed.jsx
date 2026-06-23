import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { FiBriefcase, FiSearch, FiUsers } from 'react-icons/fi';
import Header from '../../ui/Header';
import { announcementsAPI } from '../../services/api';

export default function AnnouncementsFeed() {
  const [announcements, setAnnouncements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const { data } = await announcementsAPI.getGlobalAnnouncements({ status: 'active', limit: 200 });
        setAnnouncements(data.items || []);
        setError('');
      } catch {
        setError('Не удалось загрузить ленту объявлений');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return announcements;
    return announcements.filter((item) =>
      [item.title, item.content, item.project?.project_name, item.creator?.username]
        .filter(Boolean)
        .some((v) => v.toLowerCase().includes(q))
    );
  }, [announcements, search]);

  return (
    <Header>
      <div className="max-w-6xl mx-auto space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-300 flex items-center justify-center">
            <FiBriefcase size={20} />
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl text-white font-bold">Лента объявлений</h1>
            <p className="text-gray-400 text-sm">Открытые наборы в проектные команды</p>
          </div>
        </div>

        <div className="relative">
          <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="Поиск по объявлению, проекту или workspace"
          />
        </div>

        {isLoading ? (
          <p className="text-center py-10 text-gray-400">Загрузка объявлений...</p>
        ) : error ? (
          <p className="text-center py-10 text-red-400">{error}</p>
        ) : filtered.length === 0 ? (
          <p className="text-center py-10 text-gray-400">Ничего не найдено</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map((item) => (
              <Link
                key={item.id}
                to={`/announcements/${item.id}`}
                className="p-4 rounded-xl border border-gray-700 bg-gray-800/50 hover:bg-gray-800 transition-colors"
              >
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <span className="text-xs px-2 py-1 rounded-full border border-purple-800 text-purple-300 bg-purple-900/30">
                    {item.project?.project_name || 'Проект'}
                  </span>
                  <span className="text-xs px-2 py-1 rounded-full border border-gray-700 text-gray-300 bg-gray-900/40">
                    {item.status === 'active' ? 'Активно' : item.status}
                  </span>
                </div>
                <h2 className="text-white font-semibold">{item.title}</h2>
                <p className="text-gray-400 text-sm mt-2 line-clamp-3">{item.content}</p>
                <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
                  <span className="inline-flex items-center gap-1">
                    <FiUsers />
                    {item.applications_count || 0} откликов
                  </span>
                  <span>{new Date(item.created_at).toLocaleDateString('ru-RU')}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </Header>
  );
}
