# Инструкция по добавлению ссылки на FAQ в Header.jsx

## Что нужно сделать:

1. Откройте файл `frontend/src/ui/Header.jsx`
2. Найдите иконку вопроса (GoQuestion) в двух местах:
   - В мобильном меню (строки ~57-59)
   - В десктопном меню (строки ~94-96)

## Замените:

### Мобильная версия (строки 57-59):
```jsx
<div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
<GoQuestion className="w-[30px] h-[30px] dark:text-white text-black" />
</div>
```

**ЗАМЕНИТЬ НА:**
```jsx
<Link to='/faq' onClick={() => setIsMobileMenuOpen(false)}>
    <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
    <GoQuestion className="w-[30px] h-[30px] dark:text-white text-black" />
    </div>
</Link>
```

### Десктопная версия (строки 94-96):
```jsx
<div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
<GoQuestion className="w-[30px] h-[30px] dark:text-white text-black" />
</div>
```

**ЗАМЕНИТЬ НА:**
```jsx
<Link to='/faq'>
    <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
    <GoQuestion className="w-[30px] h-[30px] dark:text-white text-black" />
    </div>
</Link>
```

## Результат:
После этих изменений иконка вопроса будет вести на страницу `/faq` и будет работать как на мобильных, так и на десктопных устройствах.

## Готово:
✅ Компонент FAQ создан с красивым дизайном
✅ Поиск по вопросам работает
✅ Выпадающие элементы с анимацией
✅ Адаптивный дизайн для темной/светлой темы
✅ Контакты и ссылки для поддержки
✅ Маршрут `/faq` добавлен в App.jsx
