import React, { useState, useMemo } from 'react';
import { GoSearch } from "react-icons/go";

export default function FAQSearch({ faqData, onItemSelect }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredResults = useMemo(() => {
    if (!searchTerm.trim()) return [];

    const results = [];
    const term = searchTerm.toLowerCase();

    Object.keys(faqData).forEach(category => {
      faqData[category].forEach(item => {
        if (item.question.toLowerCase().includes(term) || 
            item.answer.toLowerCase().includes(term) ||
            item.tags.some(tag => tag.toLowerCase().includes(term))) {
          results.push({ ...item, category });
        }
      });
    });

    return results.slice(0, 5); // Ограничиваем количество результатов
  }, [searchTerm, faqData]);

  return (
    <div className="relative w-full max-w-md">
      <div className="relative">
        <GoSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Поиск по FAQ..."
          className="w-full pl-10 pr-4 py-2 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-xl 
                     focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20
                     transition-all duration-300 text-gray-900 dark:text-white placeholder-gray-500"
        />
      </div>

      {searchTerm && filteredResults.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 max-h-96 overflow-y-auto">
          {filteredResults.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                onItemSelect(item.category, item.id);
                setSearchTerm('');
              }}
              className="w-full p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-b-0"
            >
              <div className="font-medium text-gray-900 dark:text-white mb-1">
                {item.question}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                {item.answer}
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {item.tags.slice(0, 2).map((tag, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 text-xs rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      )}

      {searchTerm && filteredResults.length === 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 p-4">
          <p className="text-center text-gray-500 dark:text-gray-400">
            Ничего не найдено по запросу "{searchTerm}"
          </p>
        </div>
      )}
    </div>
  );
}
