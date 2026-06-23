import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import Header from '../../ui/Header'
import {
  createFeedComment,
  deleteFeedComment,
  fetchFeedProjectComments,
  fetchFeedProjectDetail,
  toggleFeedCommentLike,
  toggleFeedProjectLike,
  updateFeedComment,
} from '../../store/slices/feed'
import { channelAPI, githubAPI, formatApiError } from '../../services/api'

const TEXT_MIME_PREFIXES = ['text/', 'application/json', 'application/xml', 'application/javascript']
const IMAGE_MIME_PREFIX = 'image/'

function isImageFile(mime) {
  return mime && mime.toLowerCase().startsWith(IMAGE_MIME_PREFIX)
}

function isTextFile(mime) {
  if (!mime) return false
  const m = mime.toLowerCase()
  return TEXT_MIME_PREFIXES.some((p) => m.startsWith(p))
}

function parseGitHubRepo(url) {
  if (!url) return null
  try {
    const u = new URL(url.trim())
    if (!u.hostname.includes('github.com')) return null
    const parts = u.pathname.split('/').filter(Boolean)
    if (parts.length < 2) return null
    return { owner: parts[0], repo: parts[1].replace(/\.git$/i, '') }
  } catch {
    return null
  }
}

export default function FeedProjectDetails() {
  const { projectId } = useParams()
  const dispatch = useDispatch()
  const { selectedProject, commentsByProject, repliesByProject, commentsLoading, detailLoading, detailError } = useSelector((s) => s.feed)

  const [newComment, setNewComment] = useState('')
  const [replyingToId, setReplyingToId] = useState(null)
  const [replyText, setReplyText] = useState('')
  const [editingCommentId, setEditingCommentId] = useState(null)
  const [editingText, setEditingText] = useState('')
  const [projectChannel, setProjectChannel] = useState(null)
  const [subscribing, setSubscribing] = useState(false)
  const [expandedReplies, setExpandedReplies] = useState(new Set())
  const [loadingReplies, setLoadingReplies] = useState(new Set())
  const [lightboxFile, setLightboxFile] = useState(null)
  const [textViewerFile, setTextViewerFile] = useState(null)
  const [textContent, setTextContent] = useState('')
  const [textLoading, setTextLoading] = useState(false)
  const [repoEntries, setRepoEntries] = useState([])
  const [repoPath, setRepoPath] = useState('')
  const [repoLoading, setRepoLoading] = useState(false)
  const [repoError, setRepoError] = useState('')
  const [repoFileContent, setRepoFileContent] = useState('')
  const [repoFilePath, setRepoFilePath] = useState('')
  const [repoFileLoading, setRepoFileLoading] = useState(false)
  const [readmeContent, setReadmeContent] = useState('')
  const [readmeLoading, setReadmeLoading] = useState(false)

  const postId = selectedProject?.id
  const files = useMemo(() => selectedProject?.media_files || [], [selectedProject?.media_files])
  const githubUrl = useMemo(() => {
    const links = selectedProject?.github_links
    if (Array.isArray(links) && links[0]) return links[0]
    return selectedProject?.github_url || selectedProject?.feed_github_url || ''
  }, [selectedProject])
  const githubRepo = useMemo(() => parseGitHubRepo(githubUrl), [githubUrl])

  useEffect(() => {
    if (!projectId) return
    dispatch(fetchFeedProjectDetail(projectId))
  }, [dispatch, projectId])

  useEffect(() => {
    if (!postId) return
    dispatch(fetchFeedProjectComments({ postId, limit: 100, offset: 0, parent_id: null }))
  }, [dispatch, postId])

  useEffect(() => {
    if (!selectedProject?.project_id) return
    channelAPI.getProjectChannel(selectedProject.project_id).then((r) => setProjectChannel(r?.data || null)).catch(() => setProjectChannel(null))
  }, [selectedProject?.project_id])

  const commentsKey = postId ? String(postId) : String(projectId)
  const comments = useMemo(() => commentsByProject[commentsKey] || [], [commentsByProject, commentsKey])
  const repliesMap = useMemo(() => repliesByProject[commentsKey] || {}, [repliesByProject, commentsKey])

  const loadReplies = useCallback(
    async (parentId) => {
      if (!postId || loadingReplies.has(parentId)) return
      setLoadingReplies((s) => new Set(s).add(parentId))
      try {
        await dispatch(fetchFeedProjectComments({ postId, limit: 100, offset: 0, parent_id: parentId }))
        setExpandedReplies((s) => new Set(s).add(parentId))
      } finally {
        setLoadingReplies((s) => {
          const next = new Set(s)
          next.delete(parentId)
          return next
        })
      }
    },
    [dispatch, postId, loadingReplies]
  )

  const toggleReplies = (parentId) => {
    const replies = repliesMap[String(parentId)]
    if (replies && replies.length > 0) {
      setExpandedReplies((s) => {
        const next = new Set(s)
        if (next.has(parentId)) next.delete(parentId)
        else next.add(parentId)
        return next
      })
      return
    }
    loadReplies(parentId)
  }

  const handleLoadText = useCallback(
    async (file) => {
      const url = file.url || file.download_url || file.preview_url
      if (!url) return
      setTextViewerFile(file)
      setTextLoading(true)
      setTextContent('')
      try {
        const token = localStorage.getItem('token')
        const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
        const t = await res.text()
        setTextContent(t)
      } catch {
        setTextContent('Не удалось загрузить содержимое файла.')
      } finally {
        setTextLoading(false)
      }
    },
    []
  )

  const getFileUrl = (file) => file.url || file.download_url || file.preview_url || '#'
  const getFileName = (file) => file.original_filename || file.filename || file.id
  const getMime = (file) => file.mime_type || file.content_type || ''

  const loadRepoPath = useCallback(async (path = '') => {
    if (!githubRepo) return
    setRepoLoading(true)
    setRepoError('')
    try {
      const token = localStorage.getItem('github_token')
      const data = await githubAPI.getRepositoryContents(githubRepo.owner, githubRepo.repo, path, token)
      const list = Array.isArray(data) ? data : []
      list.sort((a, b) => {
        if (a.type === b.type) return a.name.localeCompare(b.name)
        return a.type === 'dir' ? -1 : 1
      })
      setRepoEntries(list)
      setRepoPath(path)
    } catch (e) {
      setRepoError('Не удалось загрузить содержимое репозитория')
      setRepoEntries([])
    } finally {
      setRepoLoading(false)
    }
  }, [githubRepo])

  const openRepoFile = useCallback(async (path) => {
    if (!githubRepo) return
    setRepoFileLoading(true)
    setRepoFilePath(path)
    setRepoFileContent('')
    try {
      const token = localStorage.getItem('github_token')
      const data = await githubAPI.getFileContent(githubRepo.owner, githubRepo.repo, path, token)
      const text = data?.decodedContent || ''
      setRepoFileContent(text)
    } catch {
      setRepoFileContent('Не удалось открыть файл.')
    } finally {
      setRepoFileLoading(false)
    }
  }, [githubRepo])

  useEffect(() => {
    if (!githubRepo) return
    loadRepoPath('')
  }, [githubRepo, loadRepoPath])

  useEffect(() => {
    if (!githubRepo) return
    const loadReadme = async () => {
      setReadmeLoading(true)
      setReadmeContent('')
      try {
        const token = localStorage.getItem('github_token')
        const root = await githubAPI.getRepositoryContents(githubRepo.owner, githubRepo.repo, '', token)
        const readme = (Array.isArray(root) ? root : []).find((x) => x.type === 'file' && String(x.name).toLowerCase() === 'readme.md')
        if (!readme) return
        const readmeData = await githubAPI.getFileContent(githubRepo.owner, githubRepo.repo, readme.path, token)
        setReadmeContent(readmeData?.decodedContent || '')
      } catch {
        setReadmeContent('')
      } finally {
        setReadmeLoading(false)
      }
    }
    loadReadme()
  }, [githubRepo])

  const handleSubscribeChannel = async () => {
    if (!projectChannel?.id) return
    try {
      setSubscribing(true)
      await channelAPI.subscribe(projectChannel.id)
      setProjectChannel((prev) => prev ? ({ ...prev, is_subscribed: true, subscribers_count: (prev.subscribers_count || 0) + 1 }) : prev)
    } catch (e) {
      console.error('Ошибка подписки на канал', e)
      alert('Не удалось подписаться на канал проекта')
    } finally {
      setSubscribing(false)
    }
  }

  if (detailLoading) {
    return (
      <Header>
        <div className="max-w-5xl mx-auto text-gray-400">Загрузка публикации...</div>
      </Header>
    )
  }

  if (detailError || !selectedProject) {
    return (
      <Header>
        <div className="max-w-5xl mx-auto">
          <Link to="/feed" className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-200 text-sm">← Назад в ленту</Link>
          <div className="mt-6 bg-red-900/20 border border-red-800 rounded-xl p-6 text-red-200">
            {formatApiError({ response: { status: 404, data: { detail: detailError?.detail || 'Публикация не найдена' } } }, 'Не удалось загрузить страницу проекта в ленте.')}
          </div>
        </div>
      </Header>
    )
  }

  return (
    <Header>
      <div className="max-w-5xl mx-auto space-y-4 px-1 sm:px-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <Link to="/feed" className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-200 text-sm whitespace-nowrap self-start">
            ← Назад в ленту
          </Link>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => dispatch(toggleFeedProjectLike({ projectId: selectedProject.id, shouldLike: !selectedProject.is_liked_by_user }))}
              className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-200"
            >
              {selectedProject.is_liked_by_user ? '❤ Убрать лайк' : '♡ Лайк'} ({selectedProject.likes_count || 0})
            </button>
          </div>
        </div>

        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 sm:p-6">
          <h1 className="text-2xl sm:text-3xl font-bold text-white break-words">{selectedProject.name}</h1>
          <p className="text-gray-300 mt-4 whitespace-pre-wrap break-words">{selectedProject.description || 'Описание отсутствует'}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {(selectedProject.tags || []).map((tag) => (
              <span key={tag} className="px-2 py-1 text-xs bg-purple-900/40 border border-purple-800 rounded-full text-purple-300">{tag}</span>
            ))}
          </div>
        </div>

        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-semibold text-white">Канал проекта</h2>
            {projectChannel?.is_subscribed ? (
              <span className="text-xs px-2 py-1 bg-green-900/20 border border-green-800 rounded-full text-green-400">Вы подписаны</span>
            ) : null}
          </div>
          {projectChannel ? (
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex-1 min-w-0">
                <p className="text-gray-200">{projectChannel.name}</p>
                <p className="text-gray-400 text-sm">{projectChannel.description || 'Описание канала отсутствует'}</p>
              </div>
              <div className="flex items-center gap-2">
                {projectChannel.is_subscribed ? (
                  <Link
                    to="/chats"
                    state={{ openChat: { ...projectChannel, type: 'channel' } }}
                    className="px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-white text-sm"
                  >
                    Открыть канал в чатах
                  </Link>
                ) : (
                  <button
                    type="button"
                    disabled={subscribing}
                    onClick={handleSubscribeChannel}
                    className="px-3 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded-lg text-white text-sm"
                  >
                    {subscribing ? 'Подписка...' : 'Подписаться'}
                  </button>
                )}
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">Канал проекта пока не создан.</p>
          )}
        </div>

        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-xl font-semibold text-white mb-3">Файлы и материалы</h2>
          {files.length === 0 ? (
            <p className="text-gray-500 text-sm">Файлы не загружены.</p>
          ) : (
            <>
              {(() => {
                const images = files.filter((f) => isImageFile(getMime(f)))
                const textFiles = files.filter((f) => isTextFile(getMime(f)))
                const others = files.filter((f) => !isImageFile(getMime(f)) && !isTextFile(getMime(f)))
                return (
                  <div className="space-y-4">
                    {images.length > 0 && (
                      <div>
                        <p className="text-gray-400 text-sm mb-2">Фотографии</p>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                          {images.map((file) => {
                            const url = getFileUrl(file)
                            return (
                              <div
                                key={file.id}
                                className="aspect-square rounded-lg overflow-hidden border border-gray-700 bg-gray-800/50 cursor-pointer hover:ring-2 hover:ring-purple-500 transition"
                                onClick={() => url && url !== '#' && setLightboxFile(file)}
                              >
                                <img src={url} alt={getFileName(file)} className="w-full h-full object-cover" />
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                    {textFiles.length > 0 && (
                      <div>
                        <p className="text-gray-400 text-sm mb-2">Текстовые файлы</p>
                        <div className="space-y-2">
                          {textFiles.map((file) => (
                            <div key={file.id} className="flex items-center justify-between p-3 rounded-lg border border-gray-800 bg-gray-900/40">
                              <p className="text-gray-200 text-sm truncate flex-1">{getFileName(file)}</p>
                              <button
                                type="button"
                                onClick={() => handleLoadText(file)}
                                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 rounded text-xs text-white ml-2"
                              >
                                Читать
                              </button>
                              <a
                                href={getFileUrl(file)}
                                target="_blank"
                                rel="noopener noreferrer"
                                download={getFileName(file)}
                                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-200 ml-1"
                              >
                                Скачать
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {others.length > 0 && (
                      <div>
                        <p className="text-gray-400 text-sm mb-2">Другие файлы</p>
                        <div className="space-y-2">
                          {others.map((file) => (
                            <div key={file.id} className="flex items-center justify-between p-3 rounded-lg border border-gray-800 bg-gray-900/40">
                              <p className="text-gray-200 text-sm truncate flex-1">{getFileName(file)}</p>
                              <a
                                href={getFileUrl(file)}
                                target="_blank"
                                rel="noopener noreferrer"
                                download={getFileName(file)}
                                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 rounded text-xs text-white"
                              >
                                Скачать
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })()}
            </>
          )}
        </div>

        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-xl font-semibold text-white mb-3">GitHub репозиторий</h2>
          {!githubUrl ? (
            <p className="text-gray-500 text-sm">Репозиторий не указан.</p>
          ) : !githubRepo ? (
            <p className="text-red-400 text-sm">Некорректная ссылка на GitHub: {githubUrl}</p>
          ) : (
            <div className="space-y-4">
              <a
                href={githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-purple-300 hover:text-purple-200 break-all"
              >
                {githubUrl}
              </a>

              {readmeLoading ? (
                <p className="text-gray-400 text-sm">Загрузка README...</p>
              ) : readmeContent ? (
                <div className="rounded-xl border border-gray-700 bg-gray-900/70 p-4">
                  <h3 className="text-white font-semibold mb-3">README.md</h3>
                  <article className="prose prose-invert max-w-none prose-pre:bg-gray-950 prose-pre:border prose-pre:border-gray-700 prose-code:text-purple-200 prose-a:text-blue-300 hover:prose-a:text-blue-200">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                      {readmeContent}
                    </ReactMarkdown>
                  </article>
                </div>
              ) : null}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="rounded-xl border border-gray-700 bg-gray-900/60 p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-gray-300 text-sm">/{repoPath}</p>
                    {repoPath ? (
                      <button
                        type="button"
                        onClick={() => {
                          const parent = repoPath.split('/').slice(0, -1).join('/')
                          loadRepoPath(parent)
                        }}
                        className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded text-gray-200"
                      >
                        Наверх
                      </button>
                    ) : null}
                  </div>
                  {repoLoading ? (
                    <p className="text-gray-400 text-sm">Загрузка файлов...</p>
                  ) : repoError ? (
                    <p className="text-red-400 text-sm">{repoError}</p>
                  ) : (
                    <div className="space-y-1 max-h-80 overflow-auto">
                      {repoEntries.map((entry) => (
                        <button
                          key={entry.path}
                          type="button"
                          onClick={() => (entry.type === 'dir' ? loadRepoPath(entry.path) : openRepoFile(entry.path))}
                          className="w-full text-left px-2 py-1.5 rounded hover:bg-gray-800 text-sm text-gray-200"
                        >
                          {entry.type === 'dir' ? '📁' : '📄'} {entry.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="rounded-xl border border-gray-700 bg-gray-900/60 p-3">
                  <p className="text-gray-300 text-sm mb-2">{repoFilePath || 'Выберите файл справа'}</p>
                  <div className="max-h-80 overflow-auto">
                    {repoFileLoading ? (
                      <p className="text-gray-400 text-sm">Открытие файла...</p>
                    ) : repoFilePath ? (
                      <pre className="text-xs text-gray-200 whitespace-pre-wrap font-mono">{repoFileContent}</pre>
                    ) : (
                      <p className="text-gray-500 text-sm">Откройте файл из репозитория, чтобы посмотреть содержимое.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {lightboxFile && (
          <div
            className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
            onClick={() => setLightboxFile(null)}
          >
            <img
              src={getFileUrl(lightboxFile)}
              alt={getFileName(lightboxFile)}
              className="max-w-full max-h-full object-contain"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              type="button"
              className="absolute top-4 right-4 text-white text-2xl hover:text-gray-300"
              onClick={() => setLightboxFile(null)}
            >
              ✕
            </button>
          </div>
        )}

        {textViewerFile && (
          <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4">
            <div className="bg-gray-900 rounded-xl border border-gray-700 w-full max-w-2xl max-h-[80vh] flex flex-col">
              <div className="flex items-center justify-between p-3 border-b border-gray-700">
                <span className="text-white font-medium truncate">{getFileName(textViewerFile)}</span>
                <button type="button" className="text-gray-400 hover:text-white" onClick={() => setTextViewerFile(null)}>
                  ✕
                </button>
              </div>
              <div className="p-4 overflow-auto flex-1">
                {textLoading ? (
                  <p className="text-gray-400">Загрузка...</p>
                ) : (
                  <pre className="text-gray-300 text-sm whitespace-pre-wrap font-mono">{textContent}</pre>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-xl font-semibold text-white mb-3">Обсуждение проекта</h2>
          <div className="space-y-2 mb-4">
            {replyingToId && (
              <div className="flex items-center gap-2 mb-2 text-sm text-gray-400">
                <span>Ответ на комментарий</span>
                <button type="button" className="text-purple-400 hover:underline" onClick={() => { setReplyingToId(null); setReplyText('') }}>
                  Отмена
                </button>
              </div>
            )}
            <textarea
              value={replyingToId ? replyText : newComment}
              onChange={(e) => (replyingToId ? setReplyText(e.target.value) : setNewComment(e.target.value))}
              rows={3}
              placeholder={replyingToId ? 'Написать ответ...' : 'Написать комментарий к проекту...'}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm"
            />
            <button
              type="button"
              onClick={async () => {
                const text = replyingToId ? replyText : newComment
                if (!text.trim()) return
                const parentId = replyingToId || undefined
                await dispatch(
                  createFeedComment({
                    postId,
                    content: text.trim(),
                    parent_id: parentId,
                  })
                )
                if (parentId) {
                  setExpandedReplies((s) => new Set(s).add(parentId))
                  setReplyingToId(null)
                  setReplyText('')
                } else setNewComment('')
              }}
              className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm"
            >
              {replyingToId ? 'Отправить ответ' : 'Отправить комментарий'}
            </button>
          </div>

          {commentsLoading ? (
            <p className="text-gray-400 text-sm">Загрузка комментариев...</p>
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-y-auto">
              {comments.map((comment) => {
                const replies = repliesMap[String(comment.id)] || []
                const expanded = expandedReplies.has(comment.id)
                const repliesLoaded = replies.length > 0 || loadingReplies.has(comment.id)
                const rc = comment.replies_count || 0

                return (
                  <div key={comment.id} className="p-3 bg-gray-800/70 rounded-lg border border-gray-700">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-gray-200 text-sm font-medium">
                          {comment.user?.username || `${comment.user?.name || ''} ${comment.user?.lastname || ''}`.trim() || `user#${comment.user?.id || ''}`}
                        </p>
                        {editingCommentId === comment.id ? (
                          <textarea
                            value={editingText}
                            onChange={(e) => setEditingText(e.target.value)}
                            className="w-full mt-2 px-2 py-1 text-sm bg-gray-900 border border-gray-700 rounded"
                          />
                        ) : (
                          <p className="text-gray-300 text-sm mt-1">{comment.content}</p>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 flex-shrink-0">{new Date(comment.created_at).toLocaleDateString('ru-RU')}</div>
                    </div>
                    <div className="mt-2 flex items-center gap-3 text-xs flex-wrap">
                      <button
                        type="button"
                        className="text-gray-400 hover:text-pink-400"
                        onClick={() => dispatch(toggleFeedCommentLike({ commentId: comment.id, shouldLike: !comment.is_liked_by_user }))}
                      >
                        ❤ {comment.likes_count || 0}
                      </button>
                      <button
                        type="button"
                        className="text-blue-300"
                        onClick={() => setReplyingToId(comment.id)}
                      >
                        Ответить
                      </button>
                      {editingCommentId === comment.id ? (
                        <>
                          <button
                            type="button"
                            className="text-blue-300"
                            onClick={async () => {
                              await dispatch(updateFeedComment({ commentId: comment.id, content: editingText }))
                              setEditingCommentId(null)
                              setEditingText('')
                            }}
                          >
                            Сохранить
                          </button>
                          <button type="button" className="text-gray-500" onClick={() => { setEditingCommentId(null); setEditingText('') }}>Отмена</button>
                        </>
                      ) : (
                        <button type="button" className="text-blue-300" onClick={() => { setEditingCommentId(comment.id); setEditingText(comment.content || '') }}>Изменить</button>
                      )}
                      <button type="button" className="text-red-400" onClick={() => dispatch(deleteFeedComment(comment.id))}>Удалить</button>
                    </div>

                    {rc > 0 && (
                      <div className="mt-2">
                        <button
                          type="button"
                          className="text-gray-400 hover:text-purple-400 text-xs"
                          onClick={() => toggleReplies(comment.id)}
                          disabled={loadingReplies.has(comment.id)}
                        >
                          {loadingReplies.has(comment.id)
                            ? 'Загрузка...'
                            : expanded
                              ? 'Скрыть ответы'
                              : `Показать ответы (${repliesLoaded ? replies.length : rc})`}
                        </button>
                        {expanded && replies.length > 0 && (
                          <div className="mt-2 ml-4 space-y-2 border-l-2 border-gray-700 pl-3">
                            {replies.map((r) => (
                              <div key={r.id} className="p-2 bg-gray-900/60 rounded-lg border border-gray-700/70">
                                <p className="text-gray-200 text-sm font-medium">
                                  {r.user?.username || `${r.user?.name || ''} ${r.user?.lastname || ''}`.trim() || `user#${r.user?.id || ''}`}
                                </p>
                                <p className="text-gray-300 text-sm mt-1">{r.content}</p>
                                <div className="mt-1 flex items-center gap-2 text-xs">
                                  <span className="text-gray-500">{new Date(r.created_at).toLocaleDateString('ru-RU')}</span>
                                  <button
                                    type="button"
                                    className="text-gray-400 hover:text-pink-400"
                                    onClick={() => dispatch(toggleFeedCommentLike({ commentId: r.id, shouldLike: !r.is_liked_by_user }))}
                                  >
                                    ❤ {r.likes_count || 0}
                                  </button>
                                  <button type="button" className="text-blue-300" onClick={() => setReplyingToId(comment.id)}>Ответить</button>
                                  <button type="button" className="text-red-400" onClick={() => dispatch(deleteFeedComment(r.id))}>Удалить</button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
              {comments.length === 0 && <p className="text-gray-500 text-sm">Комментариев пока нет.</p>}
            </div>
          )}
        </div>
      </div>
    </Header>
  )
}
