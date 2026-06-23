import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import Header from '../../ui/Header'
import { fetchProject } from '../../store/slices/projects'
import { feedAPI, filesAPI } from '../../services/api'

export default function PublishToFeed() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { currentProject } = useSelector((s) => s.projects)

  const [form, setForm] = useState({
    description: '',
    github_url: '',
  })
  const [feedMediaFiles, setFeedMediaFiles] = useState([])
  const [selectedFileIds, setSelectedFileIds] = useState([])
  const [uploading, setUploading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!projectId) return
    dispatch(fetchProject(projectId))
  }, [dispatch, projectId])

  useEffect(() => {
    if (!currentProject) return
    setForm((prev) => ({
      description: currentProject.description || prev.description || '',
      github_url: currentProject.feed_github_url || currentProject.github_url || prev.github_url || '',
    }))
  }, [currentProject])

  useEffect(() => {
    if (!projectId) return

    const loadExistingFeedMedia = async () => {
      try {
        const { data } = await feedAPI.getPostByProject(projectId)
        const media = Array.isArray(data?.media_files) ? data.media_files : []
        if (media.length === 0) return

        setFeedMediaFiles(
          media.map((file) => ({
            id: file.id,
            original_filename: file.original_filename || file.filename || file.id,
          }))
        )
        setSelectedFileIds(media.map((file) => file.id))
      } catch {
        // Пост ещё не опубликован — это нормально
      }
    }

    loadExistingFeedMedia()
  }, [projectId])

  const feedCategory = currentProject?.category || null

  const toggleFile = (fileId) => {
    setSelectedFileIds((prev) =>
      prev.includes(fileId) ? prev.filter((id) => id !== fileId) : [...prev, fileId]
    )
  }

  const handleUploadLocalFiles = async (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    setUploading(true)
    try {
      const uploaded = []
      for (const file of files) {
        const { data } = await filesAPI.uploadFile(file, 'project_post_file')
        uploaded.push({
          id: data.file_id,
          original_filename: data.original_filename || file.name,
        })
      }
      setFeedMediaFiles((prev) => [...prev, ...uploaded])
      setSelectedFileIds((prev) => [...prev, ...uploaded.map((f) => f.id)])
    } catch (error) {
      console.error('Ошибка загрузки файлов для ленты:', error)
      alert('Не удалось загрузить один или несколько файлов')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!projectId) return
    if (!form.description.trim()) {
      alert('Заполните описание для публичной страницы')
      return
    }
    if (selectedFileIds.length === 0) {
      alert('Выберите хотя бы один файл для карточки ленты')
      return
    }

    try {
      setIsSubmitting(true)
      const trimmedGithubUrl = form.github_url?.trim()
      await feedAPI.publishProject(projectId, {
        description: form.description.trim(),
        media_file_ids: selectedFileIds,
        github_links: trimmedGithubUrl ? [trimmedGithubUrl] : null,
      })
      alert('Страница проекта опубликована в ленте')
      navigate('/feed')
    } catch (error) {
      console.error('Ошибка публикации в ленту:', error)
      alert(error?.response?.data?.detail || 'Не удалось опубликовать страницу в ленте')
    } finally {
      setIsSubmitting(false)
    }
  }

  const filesList = useMemo(() => feedMediaFiles, [feedMediaFiles])

  return (
    <Header>
      <div className="max-w-4xl mx-auto">
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-white">Публикация страницы проекта в ленту</h1>
              <p className="text-gray-400 text-sm mt-1">
                Файлы загружаются только для публичной карточки ленты и не попадают в рабочее пространство.
              </p>
            </div>
            <Link to={`/projects/${projectId}`} className="px-3 py-2 bg-red-800 hover:bg-gray-700 text-gray-200 rounded-lg text-sm">
              Назад
            </Link>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm text-gray-300 mb-2">Название для ленты (только чтение)</label>
              <input
                type="text"
                value={currentProject?.name || ''}
                disabled
                className="w-full px-4 py-3 bg-gray-700/60 border border-gray-700 rounded-xl text-white opacity-80    "
              />
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-2">Описание для публичной страницы</label>
              <textarea
                rows={5}
                value={form.description}
                onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white"
                placeholder="Опишите проект для аудитории ленты"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-2">GitHub репозиторий (опционально)</label>
              <input
                type="url"
                value={form.github_url}
                onChange={(e) => setForm((prev) => ({ ...prev, github_url: e.target.value }))}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white"
                placeholder="https://github.com/owner/repo"
              />
              <p className="text-xs text-gray-500 mt-1">
                Ссылка будет показана на странице проекта в ленте, с просмотром файлов и README.
              </p>
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-2">Категория проекта (из главного проекта)</label>
              <input
                type="text"
                value={feedCategory || ''}
                disabled
                className="w-full px-4 py-3 bg-gray-700/60 border border-gray-700 rounded-xl text-white opacity-80 cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-2">Добавить файлы для карточки ленты</label>
              <input
                type="file"
                multiple
                onChange={handleUploadLocalFiles}
                className="block w-full text-sm text-gray-300"
              />
              {uploading && <p className="text-xs text-purple-300 mt-2">Загрузка файлов...</p>}
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-2">Выберите файлы, которые будут видны в ленте</label>
              {filesList.length === 0 ? (
                <p className="text-sm text-gray-500">Файлов пока нет. Добавьте их выше.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-72 overflow-y-auto">
                  {filesList.map((file) => (
                    <label key={file.id} className="flex items-center gap-2 px-3 py-2 bg-gray-800/80 border border-gray-700 rounded-lg">
                      <input
                        type="checkbox"
                        checked={selectedFileIds.includes(file.id)}
                        onChange={() => toggleFile(file.id)}
                      />
                      <span className="text-sm text-gray-200 truncate">{file.original_filename || file.id}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => navigate(`/projects/${projectId}`)}
                className="px-5 py-3 bg-gray-800 hover:bg-gray-700 text-white rounded-xl"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-5 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl disabled:opacity-50"
              >
                {isSubmitting ? 'Публикация...' : 'Опубликовать страницу в ленте'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Header>
  )
}
