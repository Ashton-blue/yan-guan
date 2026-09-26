import { useEffect, useRef, useState, useCallback } from 'react'

/**
 * useSSE - SSE 连接 Hook
 * - 自动重连（指数退避：1s, 2s, 4s, 8s, 16s, 最大 30s）
 * - 连接状态：connecting / open / closed
 * - 事件回调 onMessage / onFileUpload / onMeetingCreated 等
 * - 组件卸载时自动关闭
 *
 * URL query 传 token（与 download 接口一致，EventSource 无法自定义 header）
 */
export type SSEConnectionState = 'connecting' | 'open' | 'closed'

export interface SSEEventMap {
  message?: (data: any) => void
  file_upload?: (data: any) => void
  meeting_created?: (data: any) => void
  action_item_assigned?: (data: any) => void
  ready?: (data: any) => void
  [key: string]: ((data: any) => void) | undefined
}

interface UseSSEOptions {
  url: string
  enabled?: boolean // 是否启用（默认 true；设 false 时不连接）
  onEvent?: SSEEventMap
  onStateChange?: (state: SSEConnectionState) => void
}

const MAX_RECONNECT_DELAY = 30000 // 30s
const BASE_RECONNECT_DELAY = 1000 // 1s

export function useSSE({ url, enabled = true, onEvent, onStateChange }: UseSSEOptions) {
  const [state, setState] = useState<SSEConnectionState>('closed')
  const esRef = useRef<EventSource | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryCountRef = useRef(0)
  const manualCloseRef = useRef(false)

  const close = useCallback(() => {
    manualCloseRef.current = true
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    setState('closed')
  }, [])

  const connect = useCallback(() => {
    if (!enabled || !url) return
    if (esRef.current && esRef.current.readyState === EventSource.OPEN) return

    manualCloseRef.current = false
    setState('connecting')

    try {
      const es = new EventSource(url, { withCredentials: false })
      esRef.current = es

      es.onopen = () => {
        retryCountRef.current = 0
        setState('open')
      }

      es.onerror = () => {
        // 连接异常：触发重连
        setState('connecting')
        if (esRef.current) {
          esRef.current.close()
          esRef.current = null
        }
        if (manualCloseRef.current) return

        const delay = Math.min(
          BASE_RECONNECT_DELAY * Math.pow(2, retryCountRef.current),
          MAX_RECONNECT_DELAY,
        )
        retryCountRef.current += 1

        reconnectTimerRef.current = setTimeout(() => {
          connect()
        }, delay)
      }

      // 通用事件分发
      const eventTypes = ['message', 'file_upload', 'meeting_created', 'action_item_assigned', 'ready']
      eventTypes.forEach((type) => {
        es.addEventListener(type, (event) => {
          try {
            const data = JSON.parse(event.data)
            const handler = onEvent?.[type]
            if (handler) handler(data)
          } catch (e) {
            console.warn('[SSE] 解析事件数据失败:', type, e)
          }
        })
      })
    } catch (e) {
      console.error('[SSE] 创建连接失败:', e)
      setState('closed')
    }
  }, [url, enabled, onEvent])

  useEffect(() => {
    onStateChange?.(state)
  }, [state, onStateChange])

  useEffect(() => {
    if (!enabled) {
      close()
      return
    }
    // 启用后首次连接
    if (!esRef.current) {
      connect()
    }
    return () => {
      close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, url])

  return { state, connect, close }
}

export default useSSE
