import React, { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity, ArrowUpRight, BarChart3, BookOpen, Check, ChevronRight,
  CircleUserRound, Heart, Mic, Plus, Send, Settings, ShieldCheck,
  Stethoscope, Users, Menu, X, Brain, MessageCircle, Trash2, Save,
  Volume2, RefreshCw
} from 'lucide-react'
import './index.css'
import './styles.css'
import { Scroller } from './components/ui/scroller'
import { VoiceChat } from './components/ui/ia-siri-chat'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let detail = 'Request failed'
    try { detail = (await res.json()).detail || detail } catch {}
    throw new Error(detail)
  }
  return res.json()
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function splitUtterances(text) {
  const parts = String(text || '').trim().split(/(?<=[.!?])\s+/)
  return parts.map(part => part.trim()).filter(Boolean)
}

function Mark() { return <div className="brand-mark" aria-hidden="true"><span /></div> }

function Orb({ speaking = false, listening = false }) {
  return <div className={`orb ${speaking ? 'speaking' : ''} ${listening ? 'listening' : ''}`}>
    <div className="orb-glow" /><div className="orb-core" />
    <div className="orb-ring ring-a" /><div className="orb-ring ring-b" />
  </div>
}

const EMPTY_PATIENT = { name:'', age:80, gender:'', marital_status:'', mood:'', conditions:'', allergies:'', mobility:'', behavioral_traits:'', preferences:'', routines:'', notes:'' }
const EMPTY_RELATIVE = { name:'', age:'', gender:'', relationship:'daughter', personality:'warm, patient, humorous', communication_style:'gentle and familiar', preferences:'family, memories, everyday life', memories:'', voice_name:'' }
const SUGGEST_TARGETS = [
  ['mood', 'Mood'],
  ['preferences', 'Preferences'],
  ['routines', 'Routines'],
  ['conditions', 'Conditions'],
  ['mobility', 'Mobility'],
  ['behavioral_traits', 'Behavioral traits'],
  ['notes', 'General notes'],
  ['relative', 'Relative / persona'],
  ['other', 'Something else'],
]

function App() {
  const [role, setRole] = useState('elderly')
  const [tab, setTab] = useState('companion')
  const [patients, setPatients] = useState([])
  const [patient, setPatient] = useState(null)
  const [relative, setRelative] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [speaking, setSpeaking] = useState(false)
  const [listening, setListening] = useState(false)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('Demo ready')
  const [mobileNav, setMobileNav] = useState(false)
  const [demoPrompt, setDemoPrompt] = useState('')
  const [patientForm, setPatientForm] = useState(EMPTY_PATIENT)
  const [relativeForm, setRelativeForm] = useState(EMPTY_RELATIVE)
  const [note, setNote] = useState('')
  const [voices, setVoices] = useState([])
  const [voiceName, setVoiceName] = useState('')
  const recognitionRef = useRef(null)
  const selectedIdRef = useRef(null)
  const listeningRef = useRef(false)
  const inputRef = useRef('')
  const wantListenRef = useRef(false)
  const transcriptRef = useRef('')
  const restartTimerRef = useRef(null)
  const audioPlayerRef = useRef(null)
  const pendingSendRef = useRef(false)

  useEffect(() => { listeningRef.current = listening }, [listening])
  useEffect(() => { inputRef.current = input }, [input])

  useEffect(() => { loadPatients() }, [])
  useEffect(() => {
    const loadVoices = () => setVoices(window.speechSynthesis?.getVoices?.() || [])
    loadVoices()
    window.speechSynthesis?.addEventListener?.('voiceschanged', loadVoices)
    return () => window.speechSynthesis?.removeEventListener?.('voiceschanged', loadVoices)
  }, [])
  useEffect(() => {
    if (selectedIdRef.current) selectPatient(selectedIdRef.current)
  }, [role])

  useEffect(() => () => {
    wantListenRef.current = false
    clearTimeout(restartTimerRef.current)
    try { recognitionRef.current?.abort?.() } catch {}
    try { recognitionRef.current?.stop?.() } catch {}
  }, [])

  async function loadPatients() {
    try {
      const data = await api('/patients')
      setPatients(data)
      if (data[0]) await selectPatient(data[0].id)
      else setStatus('Create a patient profile to begin')
    } catch { setStatus('Backend not running') }
  }

  async function selectPatient(id) {
    try {
      const p = await api(`/patients/${id}`)
      selectedIdRef.current = id
      setPatient(p)
      setPatientForm({ ...EMPTY_PATIENT, ...p })
      const nextRelative = p.relatives?.find(r => r.id === relative?.id) || p.relatives?.[0] || null
      setRelative(nextRelative)
      setRelativeForm(nextRelative ? { ...EMPTY_RELATIVE, ...nextRelative, age:nextRelative.age || '' } : EMPTY_RELATIVE)

      // Demo / elderly: always open on a blank conversation — never dump old test chat.
      if (role === 'elderly') {
        try {
          await api(`/patients/${id}/messages?user_role=elderly`, { method: 'DELETE' })
        } catch {}
        setMessages([])
        setStatus('Ready to talk')
        return
      }

      const history = await api(`/patients/${id}/messages?limit=40&user_role=${role}`)
      setMessages(history.map(m => ({ role:m.role, content:m.content, meta:m.role === 'assistant' ? { intent:m.intent, risk_level:m.risk_level } : null })))
      setStatus('Context loaded')
    } catch { setStatus('Unable to load patient') }
  }

  async function createPatient(e) {
    e.preventDefault()
    try {
      const p = await api('/patients', { method:'POST', body:JSON.stringify({ ...patientForm, age:Number(patientForm.age) }) })
      setPatients(prev => [p, ...prev]); setPatientForm(EMPTY_PATIENT); await selectPatient(p.id); setTab('management')
    } catch (err) { setStatus(err.message) }
  }

  async function savePatient(e) {
    e.preventDefault()
    if (!patient) return
    try {
      const updated = await api(`/patients/${patient.id}`, { method:'PUT', body:JSON.stringify({ ...patientForm, age:Number(patientForm.age) }) })
      setPatients(prev => prev.map(p => p.id === updated.id ? updated : p)); await selectPatient(updated.id); setStatus('Patient profile saved')
    } catch (err) { setStatus(err.message) }
  }

  async function deletePatient() {
    if (!patient || !window.confirm(`Delete ${patient.name}? This removes its local conversation and notes.`)) return
    try {
      await api(`/patients/${patient.id}`, { method:'DELETE' })
      const remaining = patients.filter(p => p.id !== patient.id)
      setPatients(remaining); setPatient(null); setMessages([]); selectedIdRef.current = remaining[0]?.id || null
      if (remaining[0]) await selectPatient(remaining[0].id)
      else setStatus('No patient selected')
    } catch (err) { setStatus(err.message) }
  }

  function startNewRelative() {
    setRelative(null)
    setRelativeForm(EMPTY_RELATIVE)
  }

  function pickRelative(item) {
    setRelative(item)
    setRelativeForm({ ...EMPTY_RELATIVE, ...item, age: item.age || '' })
  }

  async function saveRelative(e) {
    e.preventDefault()
    if (!patient) return
    try {
      const payload = { ...relativeForm, patient_id:patient.id, age:relativeForm.age ? Number(relativeForm.age) : null }
      const r = relative?.id
        ? await api(`/relatives/${relative.id}`, { method:'PUT', body:JSON.stringify(payload) })
        : await api('/relatives', { method:'POST', body:JSON.stringify(payload) })
      await selectPatient(patient.id); setRelative(r); setRelativeForm({ ...EMPTY_RELATIVE, ...r, age: r.age || '' }); setStatus('Persona saved')
    } catch (err) { setStatus(err.message) }
  }

  async function deleteRelative() {
    if (!relative || !window.confirm(`Delete persona ${relative.name}?`)) return
    try { await api(`/relatives/${relative.id}`, { method:'DELETE' }); await selectPatient(patient.id); setStatus('Persona deleted') }
    catch (err) { setStatus(err.message) }
  }

  async function addNote(e) {
    e.preventDefault()
    if (!patient || !note.trim() || role !== 'doctor') return
    try {
      await api('/notes', { method:'POST', body:JSON.stringify({ patient_id:patient.id, author:'Doctor', content:note, user_role:'doctor' }) })
      setNote(''); await selectPatient(patient.id); setStatus('Care note added')
    } catch (err) { setStatus(err.message) }
  }

  async function deleteNote(id) {
    if (role !== 'doctor') return
    try { await api(`/notes/${id}`, { method:'DELETE' }); await selectPatient(patient.id) }
    catch (err) { setStatus(err.message) }
  }

  async function addSuggestion(payload) {
    if (!patient) return
    const saved = await api('/suggestions', { method:'POST', body:JSON.stringify({
      patient_id: patient.id,
      author: payload.author || (role === 'elderly' ? patient.name : 'Relative'),
      target: payload.target,
      content: payload.content,
      user_role: role === 'doctor' ? 'relative' : role,
    }) })
    await selectPatient(patient.id)
    setStatus('Suggestion sent')
    return saved
  }

  async function sendMessage(text = input, { opener = null } = {}) {
    if (!patient || loading) return

    if (opener === 'habits') {
      setLoading(true)
      setStatus('Looking at today’s habits…')
      try {
        const data = await api('/chat', {
          method: 'POST',
          body: JSON.stringify({
            patient_id: patient.id,
            relative_id: relative?.id || null,
            message: '',
            user_role: role,
            opener: 'habits',
          }),
        })
        setMessages(prev => [...prev, { role: 'assistant', content: data.response, meta: data }])
        setStatus(`${data.intent} · habits check-in`)
        speak(data.response, data.audio_url)
      } catch (err) {
        setMessages(prev => [...prev, { role: 'assistant', content: `I couldn’t start that check-in. ${err.message}` }])
        setStatus('Pipeline error')
      } finally {
        setLoading(false)
      }
      return
    }

    const message = String(text || '').trim()
    if (!message) return
    setMessages(prev => [...prev, { role:'user', content:message }])
    setInput(''); setLoading(true); setStatus('Running the twin pipeline…')
    try {
      const data = await api('/chat', { method:'POST', body:JSON.stringify({ patient_id:patient.id, relative_id:relative?.id || null, message, user_role:role }) })
      setMessages(prev => [...prev, { role:'assistant', content:data.response, meta:data }])
      setStatus(`${data.intent} · ${data.risk_level} risk · ${data.mode}${data.policy ? ` · ${data.policy}` : ''}`)
      speak(data.response, data.audio_url)
    } catch (err) {
      setMessages(prev => [...prev, { role:'assistant', content:`I couldn't reach the conversation service. ${err.message}` }])
      setStatus('Pipeline error')
    } finally { setLoading(false) }
  }

  function startHabitsCheckIn() {
    sendMessage('', { opener: 'habits' })
  }

  async function clearChat() {
    if (!patient) return
    try {
      await api(`/patients/${patient.id}/messages?user_role=${role}`, { method:'DELETE' })
      setMessages([])
      setStatus('Fresh conversation')
    } catch (err) { setStatus(err.message) }
  }

  function stopAudio() {
    try { audioPlayerRef.current?.pause?.() } catch {}
    audioPlayerRef.current = null
    try { window.speechSynthesis?.cancel?.() } catch {}
    setSpeaking(false)
  }

  function speak(text, audioUrl) {
    const clean = String(text || '').trim()
    if (!clean) return
    stopAudio()

    const startBrowser = () => {
      if (!('speechSynthesis' in window)) {
        setStatus('This browser cannot speak aloud')
        return
      }
      const u = new SpeechSynthesisUtterance(clean)
      const selected = voices.find(v => v.name === voiceName)
      if (selected) u.voice = selected
      u.rate = role === 'elderly' ? 0.7 : 0.88
      u.pitch = 1
      u.onstart = () => setSpeaking(true)
      u.onend = () => setSpeaking(false)
      u.onerror = () => setSpeaking(false)
      window.speechSynthesis.speak(u)
    }

    // Elderly: always speak in the browser so voice and text land together.
    if (role === 'elderly') {
      startBrowser()
      return
    }

    let started = false
    if (audioUrl) {
      try {
        const origin = API.replace(/\/api\/?$/, '')
        const url = audioUrl.startsWith('http') ? audioUrl : `${origin}${audioUrl}`
        const audio = new Audio(url)
        audioPlayerRef.current = audio
        const failSafe = setTimeout(() => {
          if (!started) startBrowser()
        }, 600)
        audio.onplay = () => {
          started = true
          clearTimeout(failSafe)
          setSpeaking(true)
        }
        audio.onended = () => setSpeaking(false)
        audio.onerror = () => {
          clearTimeout(failSafe)
          setSpeaking(false)
          startBrowser()
        }
        audio.play().catch(() => {
          clearTimeout(failSafe)
          startBrowser()
        })
        return
      } catch {
        // fall through
      }
    }
    startBrowser()
  }

  function speakBrowser(text) {
    speak(text, null)
  }

  function stopListening({ send = false } = {}) {
    pendingSendRef.current = !!send
    wantListenRef.current = false
    clearTimeout(restartTimerRef.current)
    restartTimerRef.current = null
    const active = recognitionRef.current
    // Use stop() (not abort) so Chrome can flush the last transcript chunk.
    try { active?.stop?.() } catch {}
    // If recognition already idle, finish immediately.
    if (!active) {
      finishListeningSession()
    }
  }

  function finishListeningSession() {
    recognitionRef.current = null
    setListening(false)
    const spoken = (transcriptRef.current || inputRef.current).trim()
    if (spoken) {
      setInput(spoken)
      inputRef.current = spoken
    }
    const shouldSend = pendingSendRef.current
    pendingSendRef.current = false
    if (shouldSend && spoken && !loading) {
      setStatus('Sending what you said…')
      sendMessage(spoken)
    } else {
      setStatus(spoken ? 'Ready — tap Send or talk again' : 'Ready')
    }
  }

  function attachRecognitionHandlers(r, SpeechRecognition) {
    r.lang = 'en-US'
    r.interimResults = true
    // false is more reliable in Chrome for getting results; we restart on end.
    r.continuous = false
    r.maxAlternatives = 1

    r.onstart = () => {
      if (!wantListenRef.current && !pendingSendRef.current) return
      setListening(true)
      setStatus('Listening… tap the mic again when finished')
    }

    r.onresult = (event) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          transcriptRef.current = `${transcriptRef.current} ${piece}`.replace(/\s+/g, ' ').trim()
        } else {
          interim += piece
        }
      }
      const text = `${transcriptRef.current} ${interim}`.replace(/\s+/g, ' ').trim()
      if (text) {
        setInput(text)
        inputRef.current = text
      }
      setStatus(text ? `Heard: “${text.slice(0, 48)}${text.length > 48 ? '…' : ''}”` : 'Listening…')
    }

    r.onerror = (event) => {
      const err = event.error
      if (err === 'aborted') return
      if (err === 'no-speech') {
        // Keep listening open; restart happens in onend.
        setStatus('Still listening…')
        return
      }
      if (err === 'not-allowed') {
        wantListenRef.current = false
        pendingSendRef.current = false
        setListening(false)
        setStatus('Allow the microphone, then tap again')
        return
      }
      if (err === 'network') {
        setStatus('Speech needs an internet connection (Chrome speech service)')
        return
      }
      setStatus(`Mic issue (${err}) — try again`)
    }

    r.onend = () => {
      if (pendingSendRef.current || !wantListenRef.current) {
        finishListeningSession()
        return
      }
      // Keep listening: start a fresh recognition pass.
      clearTimeout(restartTimerRef.current)
      restartTimerRef.current = setTimeout(() => {
        if (!wantListenRef.current) {
          finishListeningSession()
          return
        }
        try {
          const next = new SpeechRecognition()
          recognitionRef.current = next
          attachRecognitionHandlers(next, SpeechRecognition)
          next.start()
          setListening(true)
        } catch {
          restartTimerRef.current = setTimeout(() => {
            if (!wantListenRef.current) {
              finishListeningSession()
              return
            }
            try {
              const next = new SpeechRecognition()
              recognitionRef.current = next
              attachRecognitionHandlers(next, SpeechRecognition)
              next.start()
              setListening(true)
            } catch {
              wantListenRef.current = false
              setStatus('Mic paused — tap to try again')
              finishListeningSession()
            }
          }, 350)
        }
      }, 80)
    }
  }

  function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setStatus('Use Chrome or Edge for voice typing')
      return
    }

    if (wantListenRef.current || listeningRef.current) {
      stopListening({ send: true })
      return
    }

    if (loading) return

    stopAudio()
    wantListenRef.current = true
    pendingSendRef.current = false
    transcriptRef.current = ''
    clearTimeout(restartTimerRef.current)

    const r = new SpeechRecognition()
    recognitionRef.current = r
    attachRecognitionHandlers(r, SpeechRecognition)

    try {
      r.start()
      setListening(true)
      setStatus('Listening… speak clearly, then tap the mic again')
    } catch {
      wantListenRef.current = false
      setListening(false)
      setStatus('Could not start the microphone')
    }
  }

  function startFromPrompt() {
    const text = demoPrompt.trim()
    if (!text || loading) return
    setInput(text); go('companion'); sendMessage(text)
  }

  function go(id) { setTab(id); setMobileNav(false); window.scrollTo({ top:0, behavior:'smooth' }) }

  const nav = role === 'elderly'
    ? [['companion','Talk',Heart], ['intro','How it works',BookOpen]]
    : [['intro','Overview',BookOpen], ['companion','Companion',Heart], ['management','People',Users], ['analysis','Analysis',BarChart3], ['settings','System',Settings]]

  return <div className={`app role-${role}`}>
    <div className="announcement"><span>BEHAVIORAL DIGITAL TWIN</span><span>Human-supervised MVP <ArrowUpRight size={13}/></span></div>
    <header className="nav-shell"><div className="nav-inner">
      <button className="brand" onClick={() => go(role === 'elderly' ? 'companion' : 'intro')} aria-label="Kindred home"><Mark/><span className="brand-word">Kindred</span></button>
      <nav className={`top-nav ${mobileNav ? 'open' : ''}`}>{nav.map(([id,label,Icon]) => <button key={id} className={tab===id?'active':''} onClick={() => go(id)}><Icon size={role==='elderly'?22:18}/>{label}</button>)}</nav>
      <div className="nav-actions"><button className="role-pill" onClick={() => {
        const next = role === 'elderly' ? 'relative' : role === 'relative' ? 'doctor' : 'elderly'
        setRole(next); setTab(next === 'elderly' ? 'companion' : next === 'doctor' ? 'analysis' : 'management')
      }}>{role==='elderly'?<Heart size={16}/>:role==='doctor'?<Stethoscope size={16}/>:<Users size={16}/>} {role} · demo</button><button className="mobile-menu" onClick={() => setMobileNav(v=>!v)}>{mobileNav?<X/>:<Menu/>}</button></div>
    </div></header>

    <main className="page">
      <div className="page-meta"><span>{role.toUpperCase()} EXPERIENCE</span><span className="patient-chip"><CircleUserRound size={18}/>{patient?.name || 'No patient selected'}</span></div>
      {tab==='intro' && <Intro go={go} patient={patient} demoPrompt={demoPrompt} setDemoPrompt={setDemoPrompt} startFromPrompt={startFromPrompt}/>}
      {tab==='companion' && <Companion role={role} patient={patient} relative={relative} messages={messages} loading={loading} speaking={speaking} listening={listening} status={status} input={input} setInput={setInput} sendMessage={sendMessage} startHabitsCheckIn={startHabitsCheckIn} startListening={startListening} stopListening={stopListening} speak={speak} voices={voices} voiceName={voiceName} setVoiceName={setVoiceName} clearChat={clearChat}/>}
      {tab==='management' && <Management role={role} patient={patient} patients={patients} selectPatient={selectPatient} patientForm={patientForm} setPatientForm={setPatientForm} createPatient={createPatient} savePatient={savePatient} deletePatient={deletePatient} relative={relative} relativeForm={relativeForm} setRelativeForm={setRelativeForm} pickRelative={pickRelative} startNewRelative={startNewRelative} saveRelative={saveRelative} deleteRelative={deleteRelative} addSuggestion={addSuggestion}/>}
      {tab==='analysis' && <Analysis role={role} patient={patient} note={note} setNote={setNote} addNote={addNote} deleteNote={deleteNote}/>}
      {tab==='settings' && <SettingsPanel/>}
    </main>
  </div>
}

function Intro({ go, patient, demoPrompt, setDemoPrompt, startFromPrompt }) {
  return <>
    <Scroller height="min(790px, calc(100vh - 170px))" width="100%" id="kindred-journey" className="journey-scroller" childrenClassName="journey-viewport">
      <section className="scroll-step scroll-step-hero" data-scroll-step="0"><div className="hero">
        <div className="hero-copy"><span className="eyebrow-pill">A FAMILIAR VOICE</span><h1>Someone who sounds like family, looking after you.</h1><p>Kindred speaks in the voice and manner of a loved relative — a caretaker who keeps you company and gently steers healthier habits, day by day.</p><div className="hero-actions"><button className="btn btn-dark" onClick={() => document.querySelector('#kindred-journey [data-scroll-step="1"]')?.scrollIntoView({behavior:'smooth'})}>Say hello <ArrowUpRight size={16}/></button><button className="btn btn-outline" onClick={() => go('companion')}>Start talking</button></div><div className="hero-proof"><span><Check size={14}/> Family manner</span><span><Check size={14}/> Habit coaching</span><span><Check size={14}/> Calm & clear</span></div></div>
        <div className="hero-mockup"><div className="mockup-top"><div><span className="small-label">WITH YOU NOW</span><strong>{relativeName(patient)}</strong></div><span className="live-status"><i/> ready</span></div><div className="mockup-visual"><Orb/><div className="mockup-bubble bubble-green">I’m here with you.</div><div className="mockup-bubble bubble-white">Let’s drink a little water together.</div></div><div className="mockup-footer"><span>Listening</span><span><Heart size={14}/> family caretaker</span></div></div>
      </div></section>
      <section className="scroll-step prompt-step" data-scroll-step="1"><div className="scroll-step-copy"><span className="section-label">STEP 02 · YOUR WORDS</span><h2>Start with whatever is on your mind.</h2><p>Speak naturally. Your loved one is listening — they will answer in a familiar voice and may gently remind you of healthy little habits.</p><div className="step-note"><Heart size={16}/><span>Short sentences. Clear words. No rush.</span></div></div><div className="prompt-card"><div className="prompt-card-top"><span className="eyebrow-pill">SAY SOMETHING</span><span>{demoPrompt.length}/280</span></div><label htmlFor="landing-prompt">What would you like to say?</label><textarea id="landing-prompt" maxLength={280} value={demoPrompt} onChange={e=>setDemoPrompt(e.target.value)} placeholder="Tell me about your day, or ask for a reminder to drink water…"/><div className="prompt-card-footer"><span>Nothing needs to be perfect.</span><button className="btn btn-dark" disabled={!demoPrompt.trim()} onClick={startFromPrompt}>Begin conversation <ArrowUpRight size={16}/></button></div></div></section>
      <section className="scroll-step handoff-step" data-scroll-step="2"><div className="handoff-card"><div><span className="section-label">STEP 03 · TOGETHER</span><h2>Your message becomes a real conversation.</h2><p>They will answer like family — present, patient, and ready to nudge healthier habits when it helps.</p></div><div className="handoff-flow"><div><strong>01</strong><span>Your words</span></div><ChevronRight/><div><strong>02</strong><span>Familiar voice</span></div><ChevronRight/><div><strong>03</strong><span>Gentle care</span></div></div><button className="btn btn-dark" disabled={!demoPrompt.trim()} onClick={startFromPrompt}>{demoPrompt.trim()?'Continue with my message':'Write a message first'} <ChevronRight size={16}/></button></div></section>
    </Scroller>
    <section className="proof-row"><Stat number="01" label="Familiar voice" text="Sounds like family"/><Stat number="02" label="Gentle care" text="Healthy habit nudges"/><Stat number="03" label="Calm talk" text="Slow, clear words"/></section>
    <section className="editorial-grid"><div><span className="section-label">HOW THEY CARE</span><h2>Company, then a healthy nudge.</h2><p className="lead">The conversation stays simple. Your loved one listens, answers in a familiar way, and may remind you of water, a walk, rest, or your usual routine.</p></div><div className="pipeline-list"><PipelineItem n="01" title="They know you" text="Mood, routines and preferences guide what they say."/><PipelineItem n="02" title="They listen" text="Your words come first — no rush."/><PipelineItem n="03" title="They look after you" text="Small healthier habits, one at a time."/><PipelineItem n="04" title="They stay calm" text="Clear sentences you can follow."/><PipelineItem n="05" title="They speak aloud" text="You can hear them as well as read."/></div></section>
    <section className="quiet-cta"><div><span className="section-label">READY</span><h2>{patient?`${relativeName(patient)} is ready to talk.`:'Someone familiar is ready to meet you.'}</h2></div><button className="btn btn-dark" onClick={()=>go('companion')}>Open companion <ChevronRight size={16}/></button></section>
  </>
}
function relativeName(patient){return patient?.relatives?.[0]?.name || 'Kindred'}
function Stat({number,label,text}){return <div className="stat-card"><span className="stat-number">{number}</span><div><span className="section-label">{label}</span><strong>{text}</strong></div></div>}
function PipelineItem({n,title,text}){return <div className="pipeline-item"><span>{n}</span><div><strong>{title}</strong><p>{text}</p></div><ArrowUpRight size={15}/></div>}

function Companion({ role, patient, relative, messages, loading, speaking, listening, status, input, setInput, sendMessage, startHabitsCheckIn, startListening, stopListening, speak, voices, voiceName, setVoiceName, clearChat }) {
  const elderly = role === 'elderly'
  const listRef = useRef(null)
  const [liveSentences, setLiveSentences] = useState([])
  const [livePartial, setLivePartial] = useState('')
  const [revealing, setRevealing] = useState(false)
  const revealedKey = useRef('')

  useEffect(() => {
    let cancelled = false
    const last = messages[messages.length - 1]
    if (!last || last.role !== 'assistant') {
      setLiveSentences([])
      setLivePartial('')
      setRevealing(false)
      return
    }
    const key = last.content
    if (revealedKey.current === key) return
    revealedKey.current = key
    const sentences = splitUtterances(last.content)
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches

    if (!elderly || reduced) {
      setLiveSentences(sentences)
      setLivePartial('')
      setRevealing(false)
      return
    }

    setLiveSentences([])
    setLivePartial('')
    setRevealing(true)
    ;(async () => {
      const done = []
      for (const sentence of sentences) {
        if (cancelled) return
        let buf = ''
        for (const ch of sentence) {
          if (cancelled) return
          buf += ch
          setLivePartial(buf)
          await sleep(ch === ',' || ch === ';' ? 90 : 40)
        }
        done.push(sentence)
        setLiveSentences([...done])
        setLivePartial('')
        await sleep(1150)
      }
      if (!cancelled) setRevealing(false)
    })()
    return () => { cancelled = true }
  }, [messages, elderly])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, liveSentences, livePartial, loading])

  const caretakerFirst = (relative?.name || 'Family').split(' ')[0]
  const send = () => sendMessage()
  const presenceLabel = listening ? 'I’m listening…' : (speaking || revealing) ? 'I’m talking with you…' : 'I’m right here with you.'

  return <section className={`companion-page ${elderly ? 'elderly-companion' : ''}`}>
    <div className="section-intro">
      <div>
        <span className="section-label">FAMILIAR PRESENCE</span>
        <h1>{relative?.name || 'Your companion'}</h1>
        <p>{relative?.relationship || 'family caretaker'} · here for you</p>
      </div>
      <span className="live-status"><i/> {status}</span>
    </div>

    {elderly && (
      <button
        type="button"
        className="habits-invite"
        disabled={loading || !patient}
        onClick={startHabitsCheckIn}
      >
        <span className="habits-invite-kicker"><Heart size={18}/> Check-in</span>
        <span className="habits-invite-title">Shall we see how your day is going?</span>
        <span className="habits-invite-cta">Tap to begin</span>
      </button>
    )}

    <div className={`companion-layout ${elderly ? 'is-elderly' : ''}`}>
      <div className="presence-column">
        <div className={`presence-card ${elderly ? 'presence-card-voice' : ''}`}>
          <span className="eyebrow-pill">COMPANION</span>
          {elderly ? (
            <VoiceChat
              size="lg"
              demoMode={false}
              listening={listening}
              processing={loading}
              speaking={speaking || revealing}
              onStart={startListening}
              onStop={() => stopListening({ send: true })}
              label={listening ? 'Listening…' : 'Tap to talk'}
              className="kindred-voice-chat"
            />
          ) : (
            <>
              <Orb speaking={speaking || revealing} listening={listening} />
              <p className="presence-line">{presenceLabel}</p>
            </>
          )}
          {elderly && listening && (
            <p className="audio-live"><Mic size={18}/> {input.trim() ? `Hearing you: “${input.trim().slice(0, 42)}${input.trim().length > 42 ? '…' : ''}”` : 'Listening… words will appear below'}</p>
          )}
          {elderly && (speaking || revealing) && !listening && (
            <p className="audio-live"><Volume2 size={18}/> Speaking aloud…</p>
          )}
        </div>
        <div className="talk-box">
          <label htmlFor="companion-input">{elderly ? 'Your words' : 'Talk or type here'}</label>
          <textarea
            id="companion-input"
            aria-label="Message companion"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder={elderly ? 'When you talk, your words show up here…' : 'Say what is on your mind…'}
            rows={elderly ? 4 : 3}
          />
          <div className="talk-actions">
            {!elderly && (
              <button className={`mic-button ${listening ? 'active' : ''}`} onClick={startListening} type="button">
                <Mic size={22} /> {listening ? 'Listening' : 'Speak'}
              </button>
            )}
            <button className="send-wide" disabled={loading || !input.trim()} onClick={send} type="button">
              <Send size={elderly ? 24 : 18} /> Send
            </button>
          </div>
          {!elderly && (
            <>
              <button
                className="habits-checkin"
                type="button"
                disabled={loading || !patient}
                onClick={startHabitsCheckIn}
              >
                <Activity size={18} />
                Start habits check-in
              </button>
              <p className="habits-hint">
                Uses routines, eating preferences, walking, and mood from the profile to open the chat.
              </p>
            </>
          )}
          {elderly && messages.at(-1)?.role === 'assistant' && (
            <button
              className="hear-again"
              type="button"
              onClick={() => speak(messages.at(-1).content, messages.at(-1).meta?.audio_url)}
            >
              <Volume2 size={22} /> Hear that again
            </button>
          )}
          {role !== 'elderly' && (
            <div className="voice-row">
              <label><Volume2 size={16}/> Voice</label>
              <select value={voiceName} onChange={e => setVoiceName(e.target.value)}>
                <option value="">Browser default</option>
                {voices.map(v => <option key={`${v.name}-${v.lang}`} value={v.name}>{v.name} · {v.lang}</option>)}
              </select>
              {messages.at(-1)?.role === 'assistant' && (
                <button className="text-button" type="button" onClick={() => speak(messages.at(-1).content, messages.at(-1).meta?.audio_url)}>Replay</button>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="transcript-column">
        <div className="transcript-head">
          <span className="section-label">WHAT YOU HEAR</span>
          <div className="transcript-actions">
            <strong>{revealing ? 'Reading carefully…' : speaking ? 'Speaking aloud…' : 'Conversation'}</strong>
            <button type="button" className="text-button" onClick={clearChat}>Start fresh</button>
          </div>
        </div>
        <div className="transcript-list" ref={listRef}>
          {messages.length === 0 && !loading && (
            <div className="transcript-empty">
              {elderly ? (
                <button type="button" className="habits-invite habits-invite-inline" disabled={!patient || loading} onClick={startHabitsCheckIn}>
                  <span className="habits-invite-kicker"><Heart size={20}/> Check-in</span>
                  <span className="habits-invite-title">Ready when you are.</span>
                  <span className="habits-invite-cta">Tap to begin</span>
                </button>
              ) : (
                <>
                  <MessageCircle size={28} />
                  <p>Tap the mic to talk, or start a habits check-in.</p>
                </>
              )}
            </div>
          )}
          {messages.map((m, i) => {
            const isLastAssistant = m.role === 'assistant' && i === messages.length - 1
            if (m.role === 'user') {
              return <div className="speech-card you" key={`u-${i}`}><span className="speech-kicker">You said</span><p>{m.content}</p></div>
            }
            if (isLastAssistant) return null
            return splitUtterances(m.content).map((sentence, s) => (
              <div className="speech-card kindred" key={`k-${i}-${s}`}>
                <span className="speech-kicker">{caretakerFirst}</span>
                <p>{sentence}</p>
              </div>
            ))
          })}
          {liveSentences.map((sentence, i) => (
            <div className="speech-card kindred" key={`live-${i}`}>
              <span className="speech-kicker">{caretakerFirst}</span>
              <p>{sentence}</p>
            </div>
          ))}
          {livePartial && (
            <div className="speech-card kindred live">
              <span className="speech-kicker">{caretakerFirst}</span>
              <p>{livePartial}<span className="caret" /></p>
            </div>
          )}
          {loading && !livePartial && (
            <div className="speech-card kindred">
              <span className="speech-kicker">{caretakerFirst}</span>
              <p>One moment, love…</p>
            </div>
          )}
        </div>
        {role !== 'elderly' && [...messages].reverse().find(m => m.role === 'assistant')?.meta && (
          <div className="pipeline-meta">
            <Activity size={16} /> {[...messages].reverse().find(m => m.role === 'assistant').meta.intent} · {[...messages].reverse().find(m => m.role === 'assistant').meta.risk_level} risk
          </div>
        )}
      </div>

      {role !== 'elderly' && (
        <aside className="side-stack">
          <ContextPanel patient={patient} relative={relative} role={role} />
          <div className="mini-card">
            <span className="section-label">PIPELINE</span>
            <div className="mini-flow"><span>Input</span><ChevronRight /><span>ML</span><ChevronRight /><span>Safety</span><ChevronRight /><span>Graph</span><ChevronRight /><span>LLM</span></div>
            <p>Every turn is observable and the system records intent, risk and generation mode for capstone evaluation.</p>
          </div>
        </aside>
      )}
    </div>
  </section>
}

function ContextPanel({patient,relative,role='elderly'}){return <div className="context-panel"><div className="card-heading"><div><span className="section-label">{role==='elderly'?'ABOUT YOU':'CARE CONTEXT'}</span><h3>{patient?.name||'No patient selected'}</h3></div><span className="tag">{role}</span></div><Info label="Mood" value={patient?.mood||'Not provided'}/><Info label="Preferences" value={patient?.preferences||'Not provided'}/><Info label="Routine" value={patient?.routines||'Not provided'}/><Info label="With you" value={relative?`${relative.name} · ${relative.relationship}`:'Family caretaker'}/>{role!=='elderly'&&<><Info label="Conditions" value={patient?.conditions||'None recorded'}/><Info label="Mobility" value={patient?.mobility||'Not recorded'}/><Info label="Care notes" value={`${patient?.doctor_notes?.length||0} recorded`}/></>}<div className="safety-note"><Heart size={17}/><div><strong>{role==='elderly'?'Looked after with care':'Supervisor view'}</strong><p>{role==='elderly'?'Gentle habit reminders and calm company.':'Pipeline and notes stay visible for relatives and doctors.'}</p></div></div></div>}
function Info({label,value}){return <div className="info-row"><span>{label}</span><strong>{value}</strong></div>}

function Management({
  role, patient, patients, selectPatient, patientForm, setPatientForm, createPatient, savePatient, deletePatient,
  relative, relativeForm, setRelativeForm, pickRelative, startNewRelative, saveRelative, deleteRelative, addSuggestion,
}) {
  const canEdit = role === 'doctor'
  const fields=[['name','Patient name'],['age','Age'],['gender','Gender'],['marital_status','Marital status'],['mood','Current mood'],['conditions','Conditions'],['allergies','Allergies'],['mobility','Mobility'],['behavioral_traits','Behavioral traits'],['preferences','Preferences'],['routines','Routines'],['notes','General notes']]
  const [suggestTarget, setSuggestTarget] = useState('mood')
  const [suggestText, setSuggestText] = useState('')
  const [suggestStatus, setSuggestStatus] = useState('')

  async function submitSuggestion(e) {
    e.preventDefault()
    if (!suggestText.trim()) return
    try {
      await addSuggestion({ target: suggestTarget, content: suggestText })
      setSuggestText('')
      setSuggestStatus('Suggestion saved for the care team.')
    } catch (err) {
      setSuggestStatus(err.message)
    }
  }

  return <>
    <div className="section-intro">
      <div>
        <span className="section-label">PEOPLE & PERSONAS</span>
        <h1>Patient management</h1>
        <p>{canEdit ? 'Doctors can edit profiles and add relatives. Relatives may view records and suggest changes below.' : 'You can review what has been added and suggest a change. Only a doctor can edit the official record.'}</p>
      </div>
      <span className="tag">{patients.length} patients</span>
    </div>
    <section className="management-grid">
      <div className="surface-card patient-list">
        <div className="card-heading"><h3>Patients</h3><span className="tag">{patients.length}</span></div>
        {patients.map(p => (
          <button className={`patient-row ${patient?.id===p.id?'selected':''}`} key={p.id} onClick={()=>selectPatient(p.id)}>
            <CircleUserRound size={22}/><div><strong>{p.name}</strong><span>{p.age} years · {p.mood||'mood not set'}</span></div><ChevronRight size={16}/>
          </button>
        ))}
        {patients.length===0 && <p className="muted">Create the first patient profile.</p>}
      </div>

      <form className="surface-card form-card" onSubmit={patient ? savePatient : createPatient}>
        <div className="card-heading"><div><span className="section-label">PROFILE</span><h3>{!patient ? 'Create patient' : canEdit ? 'Edit patient' : 'Patient record'}</h3></div><span className="tag">Core</span></div>
        <div className="form-grid">{fields.map(([key,label])=>(
          <label key={key}>{label}{['notes','behavioral_traits','preferences','routines'].includes(key)
            ? <textarea value={patientForm[key]||''} onChange={e=>setPatientForm({...patientForm,[key]:e.target.value})} disabled={!!patient && !canEdit}/>
            : <input type={key==='age'?'number':'text'} value={patientForm[key]||''} onChange={e=>setPatientForm({...patientForm,[key]:e.target.value})} required={key==='name'||key==='age'} disabled={!!patient && !canEdit}/>}
          </label>
        ))}</div>
        {canEdit && <div className="form-actions"><button className="btn btn-dark wide"><Save size={18}/>{patient?'Save changes':'Create patient'}</button>{patient && <button type="button" className="icon-danger" onClick={deletePatient} title="Delete patient"><Trash2 size={18}/></button>}</div>}
      </form>

      <div className="surface-card form-card">
        <div className="card-heading">
          <div><span className="section-label">PERSONA</span><h3>Relatives</h3></div>
          {(canEdit || role === 'relative') && <button type="button" className="btn btn-outline" onClick={startNewRelative}><Plus size={16}/> Add relative</button>}
        </div>
        <div className="relative-list">
          {(patient?.relatives || []).map(item => (
            <button type="button" key={item.id} className={`patient-row ${relative?.id===item.id?'selected':''}`} onClick={()=>pickRelative(item)}>
              <Users size={20}/><div><strong>{item.name}</strong><span>{item.relationship || 'relative'}</span></div>
            </button>
          ))}
          {!(patient?.relatives || []).length && <p className="muted">No relatives yet.</p>}
        </div>
        <form onSubmit={saveRelative}>
          <div className="form-grid">{Object.entries({name:'Name',age:'Age',gender:'Gender',relationship:'Relationship',personality:'Personality',communication_style:'Communication style',preferences:'Preferences',memories:'Supplied memories',voice_name:'Voice label'}).map(([key,label])=>(
            <label key={key}>{label}{['personality','communication_style','preferences','memories'].includes(key)
              ? <textarea value={relativeForm[key]||''} onChange={e=>setRelativeForm({...relativeForm,[key]:e.target.value})} disabled={!canEdit && !!relative?.id}/>
              : <input type={key==='age'?'number':'text'} value={relativeForm[key]||''} onChange={e=>setRelativeForm({...relativeForm,[key]:e.target.value})} disabled={!canEdit && !!relative?.id}/>}
            </label>
          ))}</div>
          {(canEdit || !relative?.id) && <div className="form-actions"><button className="btn btn-dark wide" disabled={!patient}><Save size={18}/>{relative?'Save persona':'Create persona'}</button>{canEdit && relative && <button type="button" className="icon-danger" onClick={deleteRelative} title="Delete persona"><Trash2 size={18}/></button>}</div>}
        </form>
      </div>
    </section>

    {role !== 'doctor' ? (
    <form className="surface-card suggest-card" onSubmit={submitSuggestion}>
      <div className="card-heading">
        <div><span className="section-label">SUGGEST CHANGES</span><h3>Ask the care team to update the record</h3></div>
      </div>
      <p className="suggest-copy">Relatives can request a correction. Doctors still make the official edit.</p>
      <div className="form-grid">
        <label>What should change?
          <select value={suggestTarget} onChange={e=>setSuggestTarget(e.target.value)}>
            {SUGGEST_TARGETS.map(([value,label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label>Your suggestion
          <textarea value={suggestText} onChange={e=>setSuggestText(e.target.value)} placeholder="Describe the change clearly…" />
        </label>
      </div>
      <button className="btn btn-dark" disabled={!patient || !suggestText.trim()}>Send suggestion</button>
      {suggestStatus && <p className="muted">{suggestStatus}</p>}
      <div className="suggestion-list">
        {(patient?.suggestions || []).map(item => (
          <div className="note" key={item.id}>
            <div className="note-head"><strong>{item.author} · {item.target}</strong><span className="tag">{item.status}</span></div>
            <p>{item.content}</p>
          </div>
        ))}
        {!(patient?.suggestions || []).length && <p className="muted">No suggestions yet.</p>}
      </div>
    </form>
    ) : (
    <div className="surface-card suggest-card">
      <div className="card-heading">
        <div><span className="section-label">SUGGEST CHANGES</span><h3>Relative requests</h3></div>
      </div>
      <p className="suggest-copy">Relatives can suggest edits. Make official changes in the forms above.</p>
      <div className="suggestion-list">
        {(patient?.suggestions || []).map(item => (
          <div className="note" key={item.id}>
            <div className="note-head"><strong>{item.author} · {item.target}</strong><span className="tag">{item.status}</span></div>
            <p>{item.content}</p>
          </div>
        ))}
        {!(patient?.suggestions || []).length && <p className="muted">No suggestions yet.</p>}
      </div>
    </div>
    )}
  </>
}

function Analysis({role, patient, note, setNote, addNote, deleteNote}){
  const [data,setData]=useState(null); const [ml,setMl]=useState(null); const [error,setError]=useState(''); const [refreshKey,setRefreshKey]=useState(0)
  useEffect(()=>{if(!patient)return; Promise.all([api(`/patients/${patient.id}/analytics`),api('/ml/metrics')]).then(([a,m])=>{setData(a);setMl(m);setError('')}).catch(e=>setError(e.message))},[patient?.id, refreshKey])
  if(!patient)return <div className="empty-state"><MessageCircle size={20}/><div><strong>No patient selected</strong><p>Create or select a patient first.</p></div></div>
  const max=Math.max(1,...(data?.daily_messages||[]).map(x=>x.n))
  const isDoctor = role === 'doctor'
  return <>
    <div className="section-intro"><div><span className="section-label">OBSERVABILITY</span><h1>Care analysis</h1><p>Observed application metrics only. These are not clinical conclusions.</p></div><button className="btn btn-outline" onClick={()=>setRefreshKey(v=>v+1)}><RefreshCw size={15}/> Refresh</button></div>
    {error&&<div className="error-banner">{error}</div>}
    <section className="analysis-grid">
      <Metric label="User messages" value={data?.user_messages??'—'} note="Stored conversation turns" progress={`${Math.min(100,(data?.user_messages||0)*5)}%`}/>
      <Metric label="Safety flags" value={data?.safety_flags??'—'} note="Medium or critical risk turns" progress={`${Math.min(100,(data?.safety_flags||0)*15)}%`} warning/>
      <Metric label="ML accuracy" value={ml?`${(ml.accuracy*100).toFixed(0)}%`:'—'} note="5-fold CV on curated baseline" progress={ml?`${ml.accuracy*100}%`:'0%'}/>
      <div className="surface-card chart-card"><div className="card-heading"><div><span className="section-label">MESSAGE VOLUME</span><h3>Recent activity</h3></div><span className="tag">Observed</span></div><div className="bar-chart">{(data?.daily_messages||[]).map(d=><div className="bar-col" key={d.day}><div className="bar" style={{height:`${Math.max(8,(d.n/max)*100)}%`}} title={`${d.day}: ${d.n} messages`}/><span>{d.day.slice(5)}</span></div>)}{!data?.daily_messages?.length&&<p className="muted">No conversation history yet.</p>}</div></div>
      <div className="surface-card"><div className="card-heading"><div><span className="section-label">INTENT DISTRIBUTION</span><h3>Observed turns</h3></div><Brain size={18}/></div>{(data?.intent_distribution||[]).map(x=><div className="distribution" key={x.intent}><span>{x.intent}</span><strong>{x.n}</strong></div>)}{!(data?.intent_distribution||[]).length&&<p className="muted">No classified assistant turns yet.</p>}<div className="analysis-footnote">ML baseline: TF-IDF + Logistic Regression. A 60–70% range is a demo target, not a clinical threshold.</div></div>
      <div className="surface-card"><div className="card-heading"><div><span className="section-label">PATIENT SNAPSHOT</span><h3>{patient.name}</h3></div><CircleUserRound size={18}/></div><Info label="Mood" value={patient.mood||'Not recorded'}/><Info label="Mobility" value={patient.mobility||'Not recorded'}/><Info label="Conditions" value={patient.conditions||'Not recorded'}/><Info label="Care notes" value={`${patient.doctor_notes?.length||0} recorded`}/></div>
      <form className="surface-card form-card note-card" onSubmit={addNote}>
        <div className="card-heading"><div><span className="section-label">DOCTOR NOTES</span><h3>Clinical care notes</h3></div><Stethoscope size={20}/></div>
        {isDoctor ? (
          <>
            <textarea value={note} onChange={e=>setNote(e.target.value)} placeholder="Add a doctor note…"/>
            <button className="btn btn-outline wide">Add note</button>
          </>
        ) : <p className="muted">Only doctors can add notes. Relatives can read what has already been recorded.</p>}
        {patient?.doctor_notes?.map(n=>(
          <div className="note" key={n.id}>
            <div className="note-head">
              <strong>{n.author}</strong>
              {isDoctor && <button type="button" className="icon-danger small" onClick={()=>deleteNote(n.id)}><Trash2 size={14}/></button>}
            </div>
            <p>{n.content}</p>
          </div>
        ))}
      </form>
    </section>
  </>
}
function Metric({label,value,note,progress,warning}){return <div className="surface-card metric"><span className="section-label">{label}</span><strong>{value}</strong><p>{note}</p><div className={`progress ${warning?'warning':''}`}><i style={{width:progress}}/></div></div>}

function SettingsPanel(){return <><div className="section-intro"><div><span className="section-label">SYSTEM</span><h1>Architecture & safety</h1><p>Supervisors see the machinery. Elderly users only hear a familiar caretaker voice.</p></div></div><section className="settings-grid"><div className="surface-card"><div className="card-heading"><div><span className="section-label">PIPELINE</span><h3>Model stack</h3></div><Brain size={18}/></div><Info label="Orchestration" value="LangGraph StateGraph"/><Info label="LLM provider" value="Groq or local demo fallback"/><Info label="ML baseline" value="TF-IDF + Logistic Regression"/><Info label="Persistence" value="SQLite"/><Info label="Voice" value="Stored TTS + browser speech"/><Info label="Roles" value="Elderly · Relative · Doctor (demo role switch)"/></div><div className="surface-card"><div className="card-heading"><div><span className="section-label">GUARDRAILS</span><h3>Safety principles</h3></div><ShieldCheck size={18}/></div><ul className="clean-list"><li>Elderly-facing replies stay in relative/caretaker character and never say “I am an AI.”</li><li>Critical-risk language still bypasses free generation.</li><li>No inventing medication names, doses, or diagnoses.</li><li>Healthy habit coaching uses only profile routines and preferences.</li><li>Missing memories stay missing rather than invented.</li><li>Relative/doctor screens remain the honest supervisor view.</li></ul></div></section></>}

createRoot(document.getElementById('root')).render(<App />)
