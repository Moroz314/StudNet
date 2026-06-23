import React, { useEffect, useState } from 'react'
import Header from '../ui/Header'
import { GoBook, GoFlame, GoMortarBoard } from "react-icons/go";
import { useNavigate } from 'react-router-dom';
import { selectIsAuth } from '../store/slices/auth';
import { useSelector } from 'react-redux';

export default function Main() {
      const [isAuth, setIsAuth] = useState(false) 
      const navigate = useNavigate();

 useEffect(() => {
    const token = localStorage.getItem('token');
    const authStatus = !!token;
    setIsAuth(authStatus);
    
    console.log('Auth status:', authStatus);

  }, [navigate]);

  const userData = {
    name: "Иван",
    surname: "Иванов",
    nickname: "@ivanov",
    avatar: "https://via.placeholder.com/150",
    university: "МГУ",
    course: "3 курс",
    faculty: "Факультет компьютерных наук",
    description: "Увлекаюсь программированием и научными исследованиями. Люблю создавать инновационные проекты и изучать новые технологии.",
    socialLinks: {
      github: "https://github.com",
      telegram: "https://t.me",
      vk: "https://vk.com",
      instagram: "https://instagram.com"
    },
    interests: ["Биология", "IT", "Наука", "Искусственный интеллект", "Data Science", "Web Development"],
    skills: ["React JS", "Python", "JavaScript", "Node.js", "MongoDB", "Docker", "Git"],
    projects: [
      {
        id: 1,
        name: "Умный помощник для студентов",
        description: "Приложение для организации учебного процесса",
        technologies: ["React", "Node.js", "MongoDB"],
        link: "#"
      },
      {
        id: 2,
        name: "Анализ биологических данных",
        description: "Система для обработки и визуализации научных данных",
        technologies: ["Python", "Pandas", "Matplotlib"],
        link: "#"
      },
      {
        id: 3,
        name: "Социальная сеть для ученых",
        description: "Платформа для collaboration между исследователями",
        technologies: ["Vue.js", "Firebase", "TypeScript"],
        link: "#"
      },
      {
        id: 4,
        name: "Мобильное приложение для трекинга привычек",
        description: "Приложение для формирования полезных привычек",
        technologies: ["React Native", "Firebase", "Redux"],
        link: "#"
      },
      {
        id: 5,
        name: "AI ассистент для исследований",
        description: "ИИ помощник для анализа научных статей",
        technologies: ["Python", "TensorFlow", "FastAPI"],
        link: "#"
      },
      {
        id: 6,
        name: "Облачная платформа для вычислений",
        description: "Платформа для распределенных вычислений",
        technologies: ["Kubernetes", "Go", "Redis"],
        link: "#"
      }
    ],
    news: [
      {
        id: 1,
        title: "Новость о запуске нового проекта",
        description: "Мы запустили новый проект по анализу данных",
        date: "15.12.2023",
        link: "#"
      },
      {
        id: 2,
        title: "Обновление платформы",
        description: "Добавлены новые функции для пользователей",
        date: "10.12.2023",
        link: "#"
      },
      {
        id: 3,
        title: "Партнерство с университетом",
        description: "Заключено партнерство с ведущим университетом",
        date: "05.12.2023",
        link: "#"
      },
      {
        id: 4,
        title: "Новые исследования",
        description: "Опубликованы результаты новых исследований",
        date: "01.12.2023",
        link: "#"
      },
      {
        id: 5,
        title: "Техническое обновление",
        description: "Проведено техническое обновление серверов",
        date: "25.11.2023",
        link: "#"
      },
      {
        id: 6,
        title: "Новые возможности",
        description: "Добавлены новые возможности для разработчиков",
        date: "20.11.2023",
        link: "#"
      }
    ]
  };
  function go_Login(){
      navigate('/login')
  }
   function go_Registr(){
      navigate('/registr')
  }

   return (
    <Header>
            <div className="bg-white dark:bg-black p-3 sm:p-4 md:p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 lg:h-[calc(100dvh-150px)]">
          {/* Проекты */}
          <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-4 sm:p-6 overflow-y-auto min-h-[280px] lg:min-h-0 lg:h-full hover:border-gray-700 transition-all duration-300 flex flex-col">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <GoBook className='text-purple-400'/>
              Мои проекты
            </h2>
            <div className="overflow-y-auto flex-1 pr-2 scrollbar-thin scrollbar-thumb-purple-600 scrollbar-track-gray-800 scrollbar-thumb-rounded-full">
              <div className="space-y-4">
                {userData.projects.map((project) => (
                  <div key={project.id} className="bg-gray-800/30 border border-gray-700 rounded-xl p-5 hover:border-purple-600/50 hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300 group">
                    <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-purple-300 transition-colors break-words">
                      {project.name}
                    </h3>
                    <p className="text-gray-400 text-sm mb-4 group-hover:text-gray-300 transition-colors">
                      {project.description}
                    </p>
                    
                    <div className="flex flex-wrap gap-2 mb-4">
                      {project.technologies.map((tech, index) => (
                        <span 
                          key={index}
                          className="px-3 py-1 bg-gray-700/50 text-gray-300 rounded-full text-xs border border-gray-600/50 group-hover:border-gray-500 transition-colors"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                    
                    <a 
                      href={project.link} 
                      className="text-purple-400 hover:text-purple-300 font-medium text-sm transition-colors flex items-center gap-1 group-hover:gap-2 duration-300"
                    >
                      Посмотреть проект 
                      <span className="group-hover:translate-x-1 transition-transform">→</span>
                    </a>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Новости */}
          <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-4 sm:p-6 overflow-y-auto min-h-[280px] lg:min-h-0 lg:h-full hover:border-gray-700 transition-all duration-300 flex flex-col ">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <GoFlame className='text-purple-400'/>
              Новости
            </h2>
            <div className="overflow-y-auto flex-1 pr-2 scrollbar-thin scrollbar-thumb-purple-600 scrollbar-track-gray-800 scrollbar-thumb-rounded-full">
              <div className="space-y-4">
                {userData.news.map((newsItem) => (
                  <div key={newsItem.id} className="bg-gray-800/30 border border-gray-700 rounded-xl p-5 hover:border-purple-600/50 hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300 group">
                    <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-purple-300 transition-colors break-words">
                      {newsItem.title}
                    </h3>
                    <p className="text-gray-400 text-sm mb-2 group-hover:text-gray-300 transition-colors">
                      {newsItem.description}
                    </p>
                    <p className="text-gray-500 text-xs mb-4">
                      {newsItem.date}
                    </p>
                    
                    <a 
                      href={newsItem.link} 
                      className="text-purple-400 hover:text-purple-300 font-medium text-sm transition-colors flex items-center gap-1 group-hover:gap-2 duration-300"
                    >
                      Читать далее 
                      <span className="group-hover:translate-x-1 transition-transform">→</span>
                    </a>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Популярные */}
          <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-4 sm:p-6 overflow-y-auto min-h-[280px] lg:min-h-0 lg:h-full hover:border-gray-700 transition-all duration-300 flex flex-col ">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <GoMortarBoard className='text-purple-400'/>
              Популярные проекты
            </h2>
            <div className="overflow-y-auto flex-1 pr-2 scrollbar-thin scrollbar-thumb-purple-600 scrollbar-track-gray-800 scrollbar-thumb-rounded-full">
              <div className="space-y-4">
                {userData.projects.slice(0, 4).map((project) => (
                  <div key={project.id} className="bg-gray-800/30 border border-gray-700 rounded-xl p-5 hover:border-purple-600/50 hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300 group">
                    <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-purple-300 transition-colors break-words">
                      {project.name}
                    </h3>
                    <p className="text-gray-400 text-sm mb-4 group-hover:text-gray-300 transition-colors">
                      {project.description}
                    </p>
                    
                    <div className="flex flex-wrap gap-2 mb-4">
                      {project.technologies.map((tech, index) => (
                        <span 
                          key={index}
                          className="px-3 py-1 bg-gray-700/50 text-gray-300 rounded-full text-xs border border-gray-600/50 group-hover:border-gray-500 transition-colors"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                    
                    <a 
                      href={project.link} 
                      className="text-purple-400 hover:text-purple-300 font-medium text-sm transition-colors flex items-center gap-1 group-hover:gap-2 duration-300"
                    >
                      Посмотреть проект 
                      <span className="group-hover:translate-x-1 transition-transform">→</span>
                    </a>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Header>
  )
}