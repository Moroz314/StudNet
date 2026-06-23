import React, { useState } from 'react';
import { GoChevronDown, GoChevronUp, GoMail, GoGlobe, GoDeviceDesktop, GoPeople, GoShield, GoClock, GoQuestion } from "react-icons/go";
import { useTheme } from '../hooks/useTheme';
import FAQSearch from './FAQSearch';
import Header from '../ui/Header';

export default function FAQ() {
  const { theme } = useTheme();
  const [activeCategory, setActiveCategory] = useState('general');
  const [expandedItems, setExpandedItems] = useState(new Set());

  const toggleItem = (itemId) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId);
    } else {
      newExpanded.add(itemId);
    }
    setExpandedItems(newExpanded);
  };

  const handleSearchSelect = (category, itemId) => {
    setActiveCategory(category);
    setExpandedItems(new Set([itemId]));
  };

  const categories = [
    { id: 'general', name: 'Общие вопросы', icon: <GoQuestion /> },
    { id: 'projects', name: 'Проекты', icon: <GoDeviceDesktop /> },
    { id: 'collaboration', name: 'Сотрудничество', icon: <GoPeople /> },
    { id: 'technical', name: 'Техническая поддержка', icon: <GoShield /> },
  ];

  const faqData = {
    general: [
      {
        id: 'g1',
        question: 'Что такое Studnet?',
        answer: 'Studnet - это социальная сеть для студентов, которая помогает находить проекты для совместной работы, общаться с единомышленниками и развивать профессиональные навыки в учебной среде.',
        tags: ['о платформе', 'назначение']
      },
      {
        id: 'g2',
        question: 'Как начать пользоваться платформой?',
        answer: 'Просто зарегистрируйтесь через email или социальные сети, подтвердите свою учетную запись и вы сможете сразу начать искать проекты и общаться с другими студентами.',
        tags: ['регистрация', 'начало работы']
      },
      {
        id: 'g3',
        question: 'Бесплатно ли пользоваться Studnet?',
        answer: 'Да, базовый функционал Studnet полностью бесплатен для всех студентов. Вы можете создавать проекты, общаться в чатах и находить партнеров без ограничений.',
        tags: ['цена', 'бесплатный доступ']
      }
    ],
    projects: [
      {
        id: 'p1',
        question: 'Как создать новый проект?',
        answer: 'Перейдите в раздел "Проекты", нажмите кнопку "Создать проект", заполните информацию о проекте: название, описание, требуемые навыки и сроки. Другие студенты смогут увидеть ваш проект и подать заявку на участие.',
        tags: ['создание', 'проект']
      },
      {
        id: 'p2',
        question: 'Как найти подходящий проект?',
        answer: 'Используйте фильтры в разделе "Проекты" для поиска по категориям, навыкам или ключевым словам. Вы также можете использовать поиск по названию или описанию проекта.',
        tags: ['поиск', 'фильтры']
      },
      {
        id: 'p3',
        question: 'Можно ли редактировать созданный проект?',
        answer: 'Да, создатель проекта может в любой момент отредактировать информацию о проекте, добавить или удалить участников, изменить сроки и требования.',
        tags: ['редактирование', 'управление']
      }
    ],
    collaboration: [
      {
        id: 'c1',
        question: 'Как найти партнеров для проекта?',
        answer: 'Используйте раздел "Найти партнеров", где вы можете отфильтровать студентов по навыкам, учебному заведению или интересам. Отправляйте приглашения интересным кандидатам.',
        tags: ['партнеры', 'команда']
      },
      {
        id: 'c2',
        question: 'Как общаться с командой проекта?',
        answer: 'Каждый проект имеет свой чат, где участники могут обмениваться сообщениями, файлами и идеями. Также доступны личные сообщения для прямого общения.',
        tags: ['общение', 'чат']
      },
      {
        id: 'c3',
        question: 'Что делать, если участник неактивен?',
        answer: 'Вы можете напомнить участнику через личное сообщение или в общем чате проекта. Если проблема сохраняется, создатель проекта может удалить неактивного участника.',
        tags: ['неактивность', 'управление']
      }
    ],
    technical: [
      {
        id: 't1',
        question: 'Какие браузеры поддерживаются?',
        answer: 'Studnet поддерживает все современные браузеры: Chrome, Firefox, Safari, Edge. Рекомендуем использовать последнюю версию браузера для лучшей производительности.',
        tags: ['браузеры', 'совместимость']
      },
      {
        id: 't2',
        question: 'Как защитить свой аккаунт?',
        answer: 'Используйте сложный пароль, включите двухфакторную аутентификацию, не передавайте свои учетные данные третьим лицам и регулярно проверяйте активность в аккаунте.',
        tags: ['безопасность', 'защита']
      },
      {
        id: 't3',
        question: 'Что делать, если возникла техническая проблема?',
        answer: 'Свяжитесь с нашей службой поддержки через форму обратной связи или напишите на support@studnet.com. Мы постараемся ответить в течение 24 часов.',
        tags: ['поддержка', 'помощь']
      }
    ]
  };

  const contactInfo = [
    {
      icon: <GoMail />,
      title: 'Email',
      value: 'support@studnet.com',
      description: 'Техническая поддержка и общие вопросы'
    },
    {
      icon: <GoGlobe />,
      title: 'Сайт',
      value: 'studnet.com',
      description: 'Официальный сайт и документация'
    },
    {
      icon: <GoClock />,
      title: 'Время работы',
      value: 'Пн-Пт, 9:00-18:00',
      description: 'Время работы службы поддержки'
    }
  ];

  return (
    <Header>
    <div className="max-w-6xl mx-auto p-4 sm:p-6">
      {/* Заголовок */}
      <div className="text-center mb-8">
        <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
          Часто задаваемые вопросы
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto mb-6">
          Найти ответы на самые популярные вопросы о платформе Studnet
        </p>
        
        {/* Поиск */}
        <div className="flex justify-center">
          <FAQSearch faqData={faqData} onItemSelect={handleSearchSelect} />
        </div>
      </div>

      {/* Категории */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => setActiveCategory(category.id)}
            className={`p-4 rounded-xl border-2 transition-all duration-300 ${
              activeCategory === category.id
                ? 'border-purple-500 bg-purple-500/10 text-purple-600 dark:text-purple-400'
                : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-purple-300 dark:hover:border-purple-600'
            }`}
          >
            <div className="flex flex-col items-center space-y-2">
              <div className="text-2xl">{category.icon}</div>
              <span className="text-sm font-medium">{category.name}</span>
            </div>
          </button>
        ))}
      </div>

      {/* FAQ Items */}
      <div className="space-y-4 mb-12">
        {faqData[activeCategory].map((item) => (
          <div
            key={item.id}
            className={`border rounded-xl transition-all duration-300 ${
              expandedItems.has(item.id)
                ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
            }`}
          >
            <button
              onClick={() => toggleItem(item.id)}
              className="w-full p-6 text-left flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-xl transition-colors"
            >
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {item.question}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {item.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="px-2 py-1 text-xs rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
              <div className="ml-4 text-purple-600 dark:text-purple-400">
                {expandedItems.has(item.id) ? (
                  <GoChevronUp className="w-6 h-6" />
                ) : (
                  <GoChevronDown className="w-6 h-6" />
                )}
              </div>
            </button>
            
            {expandedItems.has(item.id) && (
              <div className="px-6 pb-6">
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                    {item.answer}
                  </p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Контактная информация */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl p-8 text-white">
        <h2 className="text-2xl font-bold mb-6 text-center">Не нашли ответ на свой вопрос?</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {contactInfo.map((contact, index) => (
            <div key={index} className="text-center">
              <div className="flex justify-center mb-4 text-3xl">
                {contact.icon}
              </div>
              <h3 className="font-semibold text-lg mb-2">{contact.title}</h3>
              <p className="text-xl font-medium mb-2">{contact.value}</p>
              <p className="text-purple-100 text-sm">{contact.description}</p>
            </div>
          ))}
        </div>
        
        <div className="text-center mt-8">
          <button className="bg-white text-purple-600 px-8 py-3 rounded-xl font-semibold hover:bg-purple-50 transition-colors">
            Написать в поддержку
          </button>
        </div>
      </div>

      {/* Дополнительная информация */}
      <div className="mt-12 text-center">
        <p className="text-gray-500 dark:text-gray-400">
          Остались вопросы? Мы всегда рады помочь!
        </p>
        <div className="flex flex-wrap justify-center gap-4 sm:gap-6 mt-4">
          <a href="#" className="text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors">
            Политика конфиденциальности
          </a>
          <a href="#" className="text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors">
            Условия использования
          </a>
          <a href="#" className="text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors">
            Документация
          </a>
        </div>
      </div>
    </div>
    </Header>
  );
}
