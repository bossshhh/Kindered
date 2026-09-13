"use client";

import { Mic, Volume2, VolumeX, Heart, Loader2 } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

export interface VoiceChatProps {
  onStart?: () => void;
  onStop?: (duration: number) => void;
  onVolumeChange?: (volume: number) => void;
  className?: string;
  /** Auto-play demo loop. Keep false when wired to real speech recognition. */
  demoMode?: boolean;
  /** Compact layout for embedding in Companion presence card */
  compact?: boolean;
  /** large = elderly companion hero mic */
  size?: "md" | "lg";
  /** Controlled listening state from parent (Kindred mic / SpeechRecognition) */
  listening?: boolean;
  /** Controlled processing state (chat request in flight) */
  processing?: boolean;
  /** Controlled speaking / slow-reveal state */
  speaking?: boolean;
  label?: string;
}

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  opacity: number;
  velocity: { x: number; y: number };
}

export function VoiceChat({
  onStart,
  onStop,
  onVolumeChange,
  className,
  demoMode = false,
  compact = false,
  size = "md",
  listening: listeningProp,
  processing: processingProp,
  speaking: speakingProp,
  label = "Tap to talk",
}: VoiceChatProps) {
  const large = size === "lg";
  const embedded = large || compact;
  const [isListeningInternal, setIsListeningInternal] = useState(false);
  const [isProcessingInternal, setIsProcessingInternal] = useState(false);
  const [isSpeakingInternal, setIsSpeakingInternal] = useState(false);
  const [volume, setVolume] = useState(0);
  const [duration, setDuration] = useState(0);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [waveformData, setWaveformData] = useState<number[]>(Array(32).fill(0));
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const animationRef = useRef<number | null>(null);
  const durationRef = useRef(0);

  const controlled =
    listeningProp !== undefined ||
    processingProp !== undefined ||
    speakingProp !== undefined;

  const isListening = listeningProp ?? isListeningInternal;
  const isProcessing = processingProp ?? isProcessingInternal;
  const isSpeaking = speakingProp ?? isSpeakingInternal;

  useEffect(() => {
    durationRef.current = duration;
  }, [duration]);

  useEffect(() => {
    const newParticles: Particle[] = [];
    for (let i = 0; i < (large ? 24 : 12); i++) {
      newParticles.push({
        id: i,
        x: Math.random() * 400,
        y: Math.random() * 400,
        size: Math.random() * 3 + 1,
        opacity: Math.random() * 0.3 + 0.1,
        velocity: {
          x: (Math.random() - 0.5) * 0.5,
          y: (Math.random() - 0.5) * 0.5,
        },
      });
    }
    setParticles(newParticles);
  }, [large]);

  useEffect(() => {
    const animateParticles = () => {
      setParticles((prev) =>
        prev.map((particle) => ({
          ...particle,
          x: (particle.x + particle.velocity.x + 400) % 400,
          y: (particle.y + particle.velocity.y + 400) % 400,
          opacity: Math.min(
            0.5,
            Math.max(0.05, particle.opacity + (Math.random() - 0.5) * 0.02)
          ),
        }))
      );
      animationRef.current = requestAnimationFrame(animateParticles);
    };

    animationRef.current = requestAnimationFrame(animateParticles);
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, []);

  useEffect(() => {
    if (isListening) {
      intervalRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
        const newWaveform = Array(32)
          .fill(0)
          .map(() => Math.random() * 100);
        setWaveformData(newWaveform);
        const newVolume = Math.random() * 100;
        setVolume(newVolume);
        onVolumeChange?.(newVolume);
      }, 100);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setWaveformData(Array(32).fill(0));
      setVolume(0);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isListening, onVolumeChange]);

  useEffect(() => {
    if (!demoMode) return;

    let cancelled = false;

    const demoSequence = async () => {
      while (!cancelled) {
        setIsListeningInternal(true);
        onStart?.();
        await new Promise((r) => setTimeout(r, 3000));
        if (cancelled) break;

        setIsListeningInternal(false);
        setIsProcessingInternal(true);
        onStop?.(durationRef.current);
        await new Promise((r) => setTimeout(r, 2000));
        if (cancelled) break;

        setIsProcessingInternal(false);
        setIsSpeakingInternal(true);
        await new Promise((r) => setTimeout(r, 4000));
        if (cancelled) break;

        setIsSpeakingInternal(false);
        setDuration(0);
        await new Promise((r) => setTimeout(r, 2000));
      }
    };

    const timeout = setTimeout(demoSequence, 800);
    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [demoMode, onStart, onStop]);

  const handleToggleListening = () => {
    if (demoMode) return;
    // Parent owns start/stop toggle (including send-on-stop).
    if (controlled) {
      if (isProcessing) return;
      onStart?.();
      return;
    }

    if (isListeningInternal) {
      setIsListeningInternal(false);
      onStop?.(duration);
      setDuration(0);
    } else {
      setIsListeningInternal(true);
      onStart?.();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const getStatusText = () => {
    if (isListening) return "Listening… tap again when done";
    if (isProcessing) return "Thinking…";
    if (isSpeaking) return "Speaking…";
    return label;
  };

  const getStatusColor = () => {
    if (isListening) return "text-blue-500";
    if (isProcessing) return "text-amber-500";
    if (isSpeaking) return "text-emerald-600";
    return "text-muted-foreground";
  };

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center relative overflow-hidden",
        embedded ? "min-h-0 py-6 px-2 w-full" : "min-h-screen bg-background",
        className
      )}
    >
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {particles.map((particle) => (
          <motion.div
            key={particle.id}
            className="absolute w-1 h-1 bg-primary/20 rounded-full"
            style={{
              left: particle.x,
              top: particle.y,
              opacity: particle.opacity,
            }}
            animate={{ scale: [1, 1.5, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        ))}
      </div>

      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <motion.div
          className={cn(
            "rounded-full bg-gradient-to-r from-emerald-500/15 via-teal-500/10 to-sky-500/10 blur-3xl",
            large ? "w-80 h-80" : compact ? "w-48 h-48" : "w-96 h-96"
          )}
          animate={{
            scale: isListening ? [1, 1.2, 1] : [1, 1.1, 1],
            opacity: isListening ? [0.35, 0.65, 0.35] : [0.12, 0.22, 0.12],
          }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      <div
        className={cn(
          "relative z-10 flex flex-col items-center",
          large ? "space-y-6" : compact ? "space-y-4" : "space-y-8"
        )}
      >
        <motion.div
          className="relative"
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
        >
          <motion.button
            type="button"
            aria-label={getStatusText()}
            onClick={handleToggleListening}
            className={cn(
              "relative rounded-full flex items-center justify-center transition-all duration-300",
              "bg-gradient-to-br from-primary/20 to-primary/10 border-2",
              large ? "w-44 h-44 sm:w-52 sm:h-52" : compact ? "w-28 h-28" : "w-32 h-32",
              isListening
                ? "border-blue-500 shadow-lg shadow-blue-500/25"
                : isProcessing
                  ? "border-amber-500 shadow-lg shadow-amber-500/25"
                  : isSpeaking
                    ? "border-emerald-500 shadow-lg shadow-emerald-500/25"
                    : "border-border hover:border-primary/50"
            )}
            animate={{
              boxShadow: isListening
                ? [
                    "0 0 0 0 rgba(59, 130, 246, 0.4)",
                    "0 0 0 28px rgba(59, 130, 246, 0)",
                  ]
                : undefined,
            }}
            transition={{
              duration: 1.5,
              repeat: isListening ? Infinity : 0,
            }}
          >
            <AnimatePresence mode="wait">
              {isProcessing ? (
                <motion.div
                  key="processing"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                >
                  <Loader2
                    className={cn(
                      "text-amber-500 animate-spin",
                      large ? "w-16 h-16" : compact ? "w-10 h-10" : "w-12 h-12"
                    )}
                  />
                </motion.div>
              ) : isSpeaking ? (
                <motion.div
                  key="speaking"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                >
                  <Volume2
                    className={cn(
                      "text-emerald-600",
                      large ? "w-16 h-16" : compact ? "w-10 h-10" : "w-12 h-12"
                    )}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key={isListening ? "listening" : "idle"}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                >
                  <Mic
                    className={cn(
                      isListening ? "text-blue-500" : "text-muted-foreground",
                      large ? "w-16 h-16" : compact ? "w-10 h-10" : "w-12 h-12"
                    )}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.button>

          <AnimatePresence>
            {isListening && (
              <>
                <motion.div
                  className="absolute inset-0 rounded-full border-2 border-blue-500/30 pointer-events-none"
                  initial={{ scale: 1, opacity: 0.6 }}
                  animate={{ scale: 1.5, opacity: 0 }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeOut",
                  }}
                />
                <motion.div
                  className="absolute inset-0 rounded-full border-2 border-blue-500/20 pointer-events-none"
                  initial={{ scale: 1, opacity: 0.4 }}
                  animate={{ scale: 2, opacity: 0 }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeOut",
                    delay: 0.5,
                  }}
                />
              </>
            )}
          </AnimatePresence>
        </motion.div>

        <div
          className={cn(
            "flex items-center justify-center space-x-1",
            large ? "h-14" : compact ? "h-10" : "h-16"
          )}
        >
          {waveformData.map((height, index) => (
            <motion.div
              key={index}
              className={cn(
                "w-1 rounded-full transition-colors duration-300",
                large && "w-1.5",
                isListening
                  ? "bg-blue-500"
                  : isProcessing
                    ? "bg-amber-500"
                    : isSpeaking
                      ? "bg-emerald-500"
                      : "bg-muted"
              )}
              animate={{
                height: `${Math.max(4, height * (large ? 0.5 : compact ? 0.35 : 0.6))}px`,
                opacity: isListening || isSpeaking ? 1 : 0.3,
              }}
              transition={{ duration: 0.1, ease: "easeOut" }}
            />
          ))}
        </div>

        <div className="text-center space-y-1">
          <motion.p
            className={cn(
              "font-medium transition-colors",
              large ? "text-xl sm:text-2xl" : compact ? "text-base" : "text-lg",
              getStatusColor()
            )}
            animate={{ opacity: [1, 0.7, 1] }}
            transition={{
              duration: 2,
              repeat:
                isListening || isProcessing || isSpeaking ? Infinity : 0,
            }}
          >
            {getStatusText()}
          </motion.p>

          {(isListening || duration > 0) && (
            <p className="text-sm text-muted-foreground font-mono">
              {formatTime(Math.floor(duration / 10))}
            </p>
          )}

          {volume > 0 && (
            <motion.div
              className="flex items-center justify-center space-x-2 pt-1"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <VolumeX className="w-4 h-4 text-muted-foreground" />
              <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-blue-500 rounded-full"
                  animate={{ width: `${volume}%` }}
                  transition={{ duration: 0.1 }}
                />
              </div>
              <Volume2 className="w-4 h-4 text-muted-foreground" />
            </motion.div>
          )}
        </div>

        <motion.div
          className="flex items-center space-x-2 text-sm text-muted-foreground"
          animate={{ opacity: [0.55, 1, 0.55] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        >
          <Heart className="w-4 h-4 text-emerald-600" />
          <span>Family caretaker</span>
        </motion.div>
      </div>
    </div>
  );
}

export default function VoiceChatDemo() {
  return (
    <VoiceChat
      onStart={() => console.log("Voice recording started")}
      onStop={(d) => console.log(`Voice recording stopped after ${d}s`)}
      onVolumeChange={(v) => console.log(`Volume: ${v}%`)}
      demoMode={true}
    />
  );
}
