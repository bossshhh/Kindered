import React, { useEffect, useRef, useState } from 'react'

/**
 * Small, dependency-light adaptation of the 21st.dev scroller pattern.
 * It keeps native scrolling, adds snap-to-step behavior, edge fades,
 * keyboard-friendly previous/next controls, and exposes the active index.
 */
export function Scroller({
  children,
  overflow = 'y',
  height = '100%',
  width = '100%',
  className = '',
  childrenClassName = '',
  onIndexChange,
  id,
}) {
  const items = React.Children.toArray(children)
  const containerRef = useRef(null)
  const itemRefs = useRef([])
  const [index, setIndex] = useState(0)
  const [edges, setEdges] = useState({ top: false, bottom: false, left: false, right: false })

  const updateEdges = () => {
    const el = containerRef.current
    if (!el) return
    setEdges({
      top: overflow !== 'x' && el.scrollTop > 2,
      bottom: overflow !== 'x' && el.scrollTop + el.clientHeight < el.scrollHeight - 2,
      left: overflow !== 'y' && el.scrollLeft > 2,
      right: overflow !== 'y' && el.scrollLeft + el.clientWidth < el.scrollWidth - 2,
    })
  }

  const setActive = (next) => {
    const clamped = Math.max(0, Math.min(next, items.length - 1))
    setIndex(clamped)
    onIndexChange?.(clamped)
  }

  const scrollToIndex = (next) => {
    const clamped = Math.max(0, Math.min(next, items.length - 1))
    itemRefs.current[clamped]?.scrollIntoView({
      behavior: 'smooth',
      block: overflow === 'x' ? 'nearest' : 'start',
      inline: overflow === 'x' ? 'start' : 'nearest',
    })
    setActive(clamped)
  }

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    let ticking = false
    const handleScroll = () => {
      updateEdges()
      if (ticking) return
      ticking = true
      requestAnimationFrame(() => {
        const distances = itemRefs.current.map((item) => {
          if (!item) return Number.POSITIVE_INFINITY
          const rect = item.getBoundingClientRect()
          const rootRect = el.getBoundingClientRect()
          return overflow === 'x'
            ? Math.abs(rect.left - rootRect.left)
            : Math.abs(rect.top - rootRect.top)
        })
        const nearest = distances.indexOf(Math.min(...distances))
        if (nearest >= 0) setActive(nearest)
        ticking = false
      })
    }

    updateEdges()
    el.addEventListener('scroll', handleScroll, { passive: true })
    window.addEventListener('resize', updateEdges)
    return () => {
      el.removeEventListener('scroll', handleScroll)
      window.removeEventListener('resize', updateEdges)
    }
  }, [overflow, items.length])

  useEffect(() => {
    const onKeyDown = (event) => {
      const target = event.target
      if (target instanceof HTMLElement && (target.matches('input, textarea, select, button, [contenteditable=\"true\"]'))) return
      if (event.key === 'ArrowDown' && overflow !== 'x') {
        event.preventDefault()
        scrollToIndex(index + 1)
      }
      if (event.key === 'ArrowUp' && overflow !== 'x') {
        event.preventDefault()
        scrollToIndex(index - 1)
      }
      if (event.key === 'ArrowRight' && overflow !== 'y') {
        event.preventDefault()
        scrollToIndex(index + 1)
      }
      if (event.key === 'ArrowLeft' && overflow !== 'y') {
        event.preventDefault()
        scrollToIndex(index - 1)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [index, overflow, items.length])

  return (
    <div id={id} className={`scroller ${className}`} style={{ width, height }}>
      <div
        ref={containerRef}
        className={`scroller-viewport ${overflow === 'x' ? 'horizontal' : 'vertical'} ${childrenClassName}`}
        tabIndex={0}
        role="region"
        aria-label="Kindred introduction"
      >
        {items.map((child, itemIndex) => (
          <div
            key={itemIndex}
            ref={(node) => { itemRefs.current[itemIndex] = node }}
            className="scroller-item"
          >
            {child}
          </div>
        ))}
      </div>

      <div className={`scroller-fade scroller-fade-top ${edges.top ? 'visible' : ''}`} />
      <div className={`scroller-fade scroller-fade-bottom ${edges.bottom ? 'visible' : ''}`} />
      <div className={`scroller-fade scroller-fade-left ${edges.left ? 'visible' : ''}`} />
      <div className={`scroller-fade scroller-fade-right ${edges.right ? 'visible' : ''}`} />
    </div>
  )
}
