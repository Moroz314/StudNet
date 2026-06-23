import React, { useState, useRef, useEffect } from 'react'
import Header from '../../../ui/Header'
import { useLocation, useNavigate } from 'react-router-dom';
import { authAPI, formatApiError, clearAuthSession } from '../../../services/api';

export default function Registr_code() {
  const [code, setCode] = useState(['', '', '', '', '', ''])
  const [timeLeft, setTimeLeft] = useState(60)
  const [canResend, setCanResend] = useState(false)
  const inputsRef = useRef([])

      const navigate = useNavigate();

  const location = useLocation();
  const email = location.state?.email;

  // Таймер для повторной отправки
  useEffect(() => {
    if (timeLeft > 0) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000)
      return () => clearTimeout(timer)
    }
    setCanResend(true)
    setCode(['', '', '', '', '', ''])
  }, [timeLeft])

  // Обработка ввода кода
  const handleChange = (index, value) => {
    if (!/^\d?$/.test(value)) return // Только цифры
    
    const newCode = [...code]
    newCode[index] = value
    setCode(newCode)

    // Автопереход к следующему полю
    if (value && index < 5) {
      inputsRef.current[index + 1].focus()
    }

    // Если все поля заполнены
    if (newCode.every(digit => digit !== '')) {
      handleSubmit(newCode.join(''))
    }
  }

  // Обработка клавиш
  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputsRef.current[index - 1].focus()
    }
  }

  // Отправка кода
  const handleSubmit = async (fullCode) => {
    console.log('Код для проверки:', fullCode)
    const code_data = {
      email: email,
      code: fullCode
    }
    console.log(code_data)
    try {
                    const response = await authAPI.register_code(code_data);
                        
                    console.log(response, 'ewrsdffdg');
            
                    if (response.data.access_token) {
                    const token = response.data.access_token;
                    console.log(token, 'token')
                    const userId = response.data.user_id;

                    localStorage.setItem('token', token);
                    alert('вы зарегистрированы пора создать профиль')
                    navigate('/registr_profile');
                    } 
    }catch (error) {
            console.error('Registration error:', error)
            const message = formatApiError(error, 'Не удалось подтвердить код');
            alert(message);
            setCode(['', '', '', '', '', '']);
            clearAuthSession();
            navigate('/login', { state: { message } });
    }
  }

  // Повторная отправка кода
  const handleResendCode = () => {
    setTimeLeft(60)
    setCanResend(false)
    setCode(['', '', '', '', '', ''])
    inputsRef.current[0].focus()
    
    // Запрос на повторную отправку кода
    // await resendVerificationCode()
    console.log('Запрос на повторную отправку кода')
  }

  // Фокус на первое поле при загрузке
  useEffect(() => {
    inputsRef.current[0]?.focus()
  }, [])

  return (
    <Header>
      <div className=" bg-black py-8">
        <div className="max-w-md mx-auto px-4">
          {/* Заголовок */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">Код подтверждения</h1>
            <p className="text-gray-400">Введите код подтверждения отправленный на почту:</p>
          </div>

          {/* Поля для ввода кода */}
          <div className="mb-8">
            <div className="flex justify-between gap-2 mb-6">
              {code.map((digit, index) => (
                <input
                  key={index}
                  ref={el => inputsRef.current[index] = el}
                  type="text"
                  value={digit}
                  onChange={(e) => handleChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  className="w-12 h-12 text-center bg-gray-800/50 border border-gray-700 rounded-xl text-white text-xl font-semibold focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                  maxLength="1"
                  inputMode="numeric"
                  pattern="[0-9]*"
                />
              ))}
            </div>

            {/* Таймер и кнопка повторной отправки */}
            <div className="text-center">
              {!canResend ? (
                <p className="text-gray-400">
                  Отправить код повторно через <span className="text-purple-400">{timeLeft}</span> сек.
                </p>
              ) : (
                <button
                  onClick={handleResendCode}
                  className="text-purple-400 hover:text-purple-300 transition-colors duration-200 font-medium"
                >
                  Отправить код повторно
                </button>
              )}
            </div>
          </div>

          {/* Кнопка подтверждения (альтернативный вариант) */}
          <div className="mt-8">
            <button
              onClick={() => handleSubmit(code.join(''))}
              disabled={!code.every(digit => digit !== '')}
              className="w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all duration-300 transform hover:scale-[1.02] disabled:hover:scale-100"
            >
              Подтвердить
            </button>
          </div>
        </div>
      </div>
    </Header>
  )
}