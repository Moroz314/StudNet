import React, { useState } from 'react'
import Header from '../../../ui/Header'
import { FaUser, FaGithub, FaTelegram, FaVk, FaInstagram, FaUniversity } from "react-icons/fa";
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { createProfile, fetchProfile, uploadAvatar } from '../../../store/slices/profile'
 

export default function Registration_profile() {
  const [isDragOver, setIsDragOver] = useState(false);
  const [avatar, setAvatar] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();
  const dispatch = useDispatch()


  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleAvatarChange({ target: { files: [file] } });
    }
  };

  const handleAvatarChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAvatar(file);
      // Создаем превью
      const reader = new FileReader();
      reader.onload = (e) => setAvatarPreview(e.target.result);
      reader.readAsDataURL(file);
    }
  };

  const UploadAvatar = async () => {
    if (!avatar) return null;
    
    const formData = new FormData();
    formData.append('avatar', avatar);
    
    try {
      setUploading(true);
      const response = await dispatch(uploadAvatar(formData)).unwrap();
      console.log('Аватар загружен успешно:', response);
      return response;
    } catch (error) {
      console.error('Ошибка загрузки аватарки:', error);
      throw error;
    } finally {
      setUploading(false);
    }
  };

  const [formData, setFormData] = useState({
    name: '',
    lastname: '',
    username: '',
    avatar_path: '', // Только строка с путем к файлу
    birth_date: '',
    university: '',
    faculty: '',
    course: 0,
    info: '',
    links: [],
    interests: [],
    skills: [],
  });

  // Остальные состояния...
  const [tempLinks, setTempLinks] = useState({
    github: '', telegram: '', vk: '', instagram: ''
  });
  const [newInterest, setNewInterest] = useState('');
  const [newSkill, setNewSkill] = useState('');

  // Обработчики остаются без изменений...
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSocialChange = (e) => {
    const { name, value } = e.target;
    setTempLinks(prev => ({ ...prev, [name]: value }));
  };

  const handleDateChange = (e) => {
    setFormData(prev => ({ ...prev, birth_date: e.target.value }));
  };

  const addInterest = () => {
    if (newInterest.trim() && !formData.interests.includes(newInterest.trim())) {
      setFormData(prev => ({
        ...prev,
        interests: [...prev.interests, newInterest.trim()]
      }));
      setNewInterest('');
    }
  };

  const removeInterest = (interestToRemove) => {
    setFormData(prev => ({
      ...prev,
      interests: prev.interests.filter(interest => interest !== interestToRemove)
    }));
  };

  const addSkill = () => {
    if (newSkill.trim() && !formData.skills.includes(newSkill.trim())) {
      setFormData(prev => ({
        ...prev,
        skills: [...prev.skills, newSkill.trim()]
      }));
      setNewSkill('');
    }
  };

  const removeSkill = (skillToRemove) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter(skill => skill !== skillToRemove)
    }));
  };

  const prepareLinksForSubmit = () => {
    const linksArray = [];
    if (tempLinks.github.trim()) linksArray.push(tempLinks.github.trim());
    if (tempLinks.telegram.trim()) linksArray.push(tempLinks.telegram.trim());
    if (tempLinks.vk.trim()) linksArray.push(tempLinks.vk.trim());
    if (tempLinks.instagram.trim()) linksArray.push(tempLinks.instagram.trim());
    return linksArray;
  };

const handleSubmit = async (e) => {
  e.preventDefault();
  
  try {
    setUploading(true);

    // 1. Сначала создаем профиль (без avatar_path) — backend хранит связь через avatar_file_id
    const profileData = {
      name: formData.name,
      lastname: formData.lastname,
      username: formData.username,
      birth_date: formData.birth_date,
      university: formData.university,
      faculty: formData.faculty,
      course: formData.course,
      info: formData.info,
      links: prepareLinksForSubmit(),
      interests: formData.interests,
      skills: formData.skills,
    };

    console.log('Создаем профиль с данными:', profileData);
    
    await dispatch(createProfile(profileData)).unwrap();
    console.log('Профиль создан');

    // 2. После создания профиля загружаем аватар (если выбран)
    if (avatar) {
      try {
        console.log('Загружаем аватар после создания профиля...');
        await UploadAvatar();
      } catch (avatarError) {
        console.error('Ошибка загрузки аватарки:', avatarError);
        alert('Профиль создан, но аватарку не удалось загрузить');
      }
    }

    // 3. Подтягиваем актуальный профиль (с avatar_url)
    const profileResponse = await dispatch(fetchProfile()).unwrap();
    
    localStorage.setItem('profile', JSON.stringify(profileResponse));
    alert('Профиль успешно создан!');
    navigate('/profile');
    
  } catch (error) {
    console.error('Ошибка создания профиля:', error);
    console.error('Детали ошибки:', error.response?.data);
    
    // Более информативное сообщение об ошибке
    let errorMessage = 'Ошибка при создании профиля';
    if (error.response?.data?.detail) {
      if (Array.isArray(error.response.data.detail)) {
        errorMessage = error.response.data.detail.map(err => err.msg).join(', ');
      } else {
        errorMessage = error.response.data.detail;
      }
    } else if (error.message) {
      errorMessage = error.message;
    }
    
    alert(errorMessage);
  } finally {
    setUploading(false);
  }
};

  const handleKeyPress = (e, callback) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      callback();
    }
  };

  return (
    <Header>
      <div className="bg-black py-8">
        <div className="max-w-4xl mx-auto">
          {/* Заголовок */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">Создание профиля</h1>
            <p className="text-gray-400">Заполните информацию о себе</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Основная информация */}
            <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
              <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <FaUser className="text-purple-400" />
                Основная информация
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Поля имени, фамилии, никнейма */}
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">
                    Имя *
                  </label>
                  <input 
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                    placeholder="Введите имя"
                  />
                </div>
                
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">
                    Фамилия *
                  </label>
                  <input 
                    type="text"
                    name="lastname"
                    value={formData.lastname}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                    placeholder="Введите фамилию"
                  />
                </div>
                
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">
                    Никнейм *
                  </label>
                  <input 
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                    placeholder="@username"
                  />
                </div>
              </div>
            </div>

            {/* Секция аватарки */}
            <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
              <h2 className="text-xl font-bold text-white mb-4">Аватарка</h2>
              
              <div className="flex flex-col md:flex-row items-center gap-6">
                {/* Превью аватарки */}
                <div className="flex-shrink-0">
                  <div className="w-24 h-24 rounded-full bg-gray-800 border-2 border-gray-700 overflow-hidden">
                    {avatarPreview ? (
                      <img 
                        src={avatarPreview} 
                        alt="Preview" 
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-500">
                        <FaUser size={32} />
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Область загрузки */}
                <div className="flex-1">
                  <div
                    className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${
                      isDragOver ? 'border-purple-500 bg-purple-500/10' : 'border-gray-700 hover:border-gray-600'
                    }`}
                    onDrop={handleDrop}
                    onDragOver={(e) => {
                      e.preventDefault();
                      setIsDragOver(true);
                    }}
                    onDragLeave={() => setIsDragOver(false)}
                    onClick={() => document.getElementById('avatar-input').click()}
                  >
                    <input 
                      type="file" 
                      id="avatar-input"
                      accept="image/*"
                      onChange={handleAvatarChange} 
                      className="hidden" 
                    />
                    
                    {avatar ? (
                      <div className="text-center">
                        <div className="text-green-400 mb-2">✓ Файл выбран</div>
                        <div className="text-gray-300 text-sm mb-2">{avatar.name}</div>
                        <button 
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setAvatar(null);
                            setAvatarPreview(null);
                          }}
                          className="text-red-400 hover:text-red-300 text-sm"
                        >
                          Удалить
                        </button>
                      </div>
                    ) : (
                      <div>
                        <div className="text-gray-400 mb-2">
                          Перетащите аватар сюда или нажмите для выбора
                        </div>
                        <div className="text-purple-400 text-sm">
                          PNG, JPG до 5MB
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {uploading && (
                    <div className="mt-3 text-purple-400 text-sm">
                      Загрузка аватарки...
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Дата рождения */}
            <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
              <h2 className="text-xl font-bold text-white mb-4">
                Дата рождения
              </h2>   
              <input 
                type="date"
                onChange={handleDateChange}
                value={formData.birth_date}
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Образование */}
            <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
              <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <FaUniversity className="text-purple-400" />
                Образование
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">
                    Университет
                  </label>
                  <input 
                    type="text"
                    name="university"
                    value={formData.university}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                    placeholder="Название вуза"
                  />
                </div>
                
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">
                    Курс
                  </label>
                  <select 
                    name="course"
                    value={formData.course}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                  >
                    <option value={0}>Выберите курс</option>
                    {[1, 2, 3, 4, 5, 6].map(course => (
                      <option key={course} value={course} className="bg-gray-800">
                        {course} курс
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">
                    Факультет
                  </label>
                  <input 
                    type="text"
                    name="faculty"
                    value={formData.faculty}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                    placeholder="Название факультета"
                  />
                </div>
              </div>
            </div>

            {/* Описание */}
            <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
              <h2 className="text-xl font-bold text-white mb-4">О себе</h2>
              <textarea 
                name="info"
                value={formData.info}
                onChange={handleInputChange}
                rows="4"
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm resize-none"
                placeholder="Расскажите о себе, своих увлечениях и целях..."
              />
            </div>

            {/* Соцсети */}
            <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
              <h2 className="text-xl font-bold text-white mb-6">Социальные сети</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2 flex items-center gap-2">
                    <FaGithub className="text-gray-400" />
                    GitHub
                  </label>
                  <input 
                    type="url"
                    name="github"
                    value={tempLinks.github}
                    onChange={handleSocialChange}
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                    placeholder="https://github.com/username"
                  />
                </div>
                
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2 flex items-center gap-2">
                    <FaTelegram className="text-gray-400" />
                    Telegram
                  </label>
                  <input 
                    type="url"
                    name="telegram"
                    value={tempLinks.telegram}
                    onChange={handleSocialChange}
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                    placeholder="https://t.me/username"
                  />
                </div>
                
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2 flex items-center gap-2">
                    <FaVk className="text-gray-400" />
                    VK
                  </label>
                  <input 
                    type="url"
                    name="vk"
                    value={tempLinks.vk}
                    onChange={handleSocialChange}
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                    placeholder="https://vk.com/username"
                  />
                </div>
                
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2 flex items-center gap-2">
                    <FaInstagram className="text-gray-400" />
                    Instagram
                  </label>
                  <input 
                    type="url"
                    name="instagram"
                    value={tempLinks.instagram}
                    onChange={handleSocialChange}
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                    placeholder="https://instagram.com/username"
                  />
                </div>
              </div>
            </div>

            {/* Интересы */}
            <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
              <h2 className="text-xl font-bold text-white mb-4">Интересы</h2>
              
              <div className="flex flex-wrap gap-3 mb-4">
                {formData.interests.map((interest, index) => (
                  <span 
                    key={index}
                    className="px-4 py-2 bg-purple-900/40 text-purple-300 rounded-full text-sm font-medium border border-purple-800/50 flex items-center gap-2"
                  >
                    {interest}
                    <button 
                      type="button"
                      onClick={() => removeInterest(interest)}
                      className="text-purple-200 hover:text-white transition-colors"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              
              <div className="flex gap-2">
                <input 
                  type="text"
                  value={newInterest}
                  onChange={(e) => setNewInterest(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, addInterest)}
                  className="flex-1 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                  placeholder="Добавить интерес..."
                />
                <button 
                  type="button"
                  onClick={addInterest}
                  className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition-all duration-300"
                >
                  Добавить
                </button>
              </div>
            </div>

            {/* Навыки */}
            <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
              <h2 className="text-xl font-bold text-white mb-4">Навыки</h2>
              
              <div className="flex flex-wrap gap-3 mb-4">
                {formData.skills.map((skill, index) => (
                  <span 
                    key={index}
                    className="px-4 py-2 bg-blue-900/40 text-blue-300 rounded-full text-sm font-medium border border-blue-800/50 flex items-center gap-2"
                  >
                    {skill}
                    <button 
                      type="button"
                      onClick={() => removeSkill(skill)}
                      className="text-blue-200 hover:text-white transition-colors"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              
              <div className="flex gap-2">
                <input 
                  type="text"
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, addSkill)}
                  className="flex-1 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                  placeholder="Добавить навык..."
                />
                <button 
                  type="button"
                  onClick={addSkill}
                  className="px-6 py-2 bg-blue-600 hover:blue-700 text-white rounded-xl transition-all duration-300"
                >
                  Добавить
                </button>
              </div>
            </div>
       <div className="text-center">
              <button 
                type="submit"
                disabled={uploading}
                className={`px-8 py-4 text-white font-bold rounded-xl transition-all duration-300 hover:scale-105 shadow-lg ${
                  uploading 
                    ? 'bg-gray-600 cursor-not-allowed' 
                    : 'bg-purple-600 hover:bg-purple-700 shadow-purple-500/20'
                }`}
              >
                {uploading ? 'Загрузка...' : 'Создать профиль'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Header>
  )
}