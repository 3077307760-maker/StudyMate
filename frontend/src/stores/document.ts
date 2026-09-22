import { ref } from 'vue'
import { defineStore } from 'pinia'

import { api, ApiError } from '@/api'
import type { Document } from '@/types'

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<Document[]>([])
  const uploading = ref(false)
  const error = ref('')

  async function fetchDocuments(courseId: string) {
    documents.value = await api.documents(courseId)
  }

  async function upload(courseId: string, file: File) {
    uploading.value = true
    error.value = ''
    try {
      const document = await api.uploadDocument(courseId, file)
      documents.value.unshift(document)
      return document
    } catch (err) {
      error.value = err instanceof ApiError ? err.payload.message : '上传失败。'
      throw err
    } finally {
      uploading.value = false
    }
  }

  async function refreshOne(documentId: string) {
    const document = await api.document(documentId)
    const index = documents.value.findIndex((item) => item.id === documentId)
    if (index >= 0) documents.value[index] = document
    return document
  }

  async function remove(documentId: string) {
    await api.deleteDocument(documentId)
    documents.value = documents.value.filter((item) => item.id !== documentId)
  }

  async function reindex(documentId: string) {
    const document = await api.reindexDocument(documentId)
    const index = documents.value.findIndex((item) => item.id === documentId)
    if (index >= 0) documents.value[index] = document
    window.setTimeout(() => refreshOne(documentId), 1200)
    return document
  }

  return { documents, uploading, error, fetchDocuments, upload, refreshOne, remove, reindex }
})
