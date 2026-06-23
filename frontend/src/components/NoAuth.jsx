import React from 'react'
import { Link } from 'react-router-dom'
import Header from '../ui/Header'

export default function NoAuth() {
  return (
            <Header>
                <div className="bg-black p-4 sm:p-6 min-h-[calc(100dvh-70px)] w-full flex items-center justify-center">
                          <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 w-full max-w-md hover:border-gray-700 transition-all duration-300 flex items-center justify-center">
                          <div className="grid grid-cols-1 gap-10">
                                <h1 className='text-2xl text-center'>STUDNET</h1>
                                  <div className="text-center">
                                  <Link to='/login'>
                                      <button 
                                      type="button"
                                      className="px-8 py-4 w-full bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-xl transition-all duration-300 hover:scale-105 shadow-lg shadow-purple-500/20"
                                      >
                                      Войти
                                      </button>
                                  </Link>
                                </div>
                                <div className="text-center">
                                  <Link to='/registr'>
                                      <button 
                                      type="button"
                                      className="px-8 py-4 w-full bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-xl transition-all duration-300 hover:scale-105 shadow-lg shadow-purple-500/20"
                                      >
                                      Зарегистрироваться
                                      </button>
                                  </Link>
                                </div>
                          </div>
                          </div>
                      </div>
            </Header>
  )
}
