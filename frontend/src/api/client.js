import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export default {
  // CAPTCHA
  getCaptcha: () => api.get('/captcha/'),

  // Comments
  getComments: (params = {}) => api.get('/comments/', { params }),
  getCommentTree: (id) => api.get(`/comments/${id}/tree/`),
  createComment: (data) => {
    // multipart if file attached, json otherwise
    if (data.file) {
      const form = new FormData()
      Object.entries(data).forEach(([k, v]) => { if (v != null) form.append(k, v) })
      return api.post('/comments/', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    }
    return api.post('/comments/', data)
  },
}
