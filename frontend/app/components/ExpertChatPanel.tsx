"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Send,
  ChevronDown,
  X,
  Bot,
  User,
  Stethoscope,
  Mic,
  MicOff,
  Volume2,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { askAgent } from "../lib/api";
import { useActivePatient } from "../hooks/useActivePatient";

const EXPERTS = [
  { id: "general physician", label: "General Physician", color: "text-primary" },
  { id: "cardiology", label: "Cardiologist", color: "text-destructive" },
  { id: "pulmonary", label: "Pulmonologist", color: "text-vital-green" },
  { id: "obstetrics", label: "OB / Gynecologist", color: "text-pink-500" },
  { id: "dermatology", label: "Dermatologist", color: "text-orange-500" },
  { id: "neurology", label: "Neurologist", color: "text-violet-500" },
  { id: "ocular", label: "Ocular Expert", color: "text-cyan-glow" },
];

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function ExpertChatPanel() {
  const { patientId } = useActivePatient();
  const [open, setOpen] = useState(false);
  const [expert, setExpert] = useState(EXPERTS[0]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: `Hello, I'm your **${EXPERTS[0].label}** AI assistant powered by the MedVerse multi-agent system. I have access to your real-time vest telemetry. How can I help you today?`,
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const recognitionRef = useRef<any>(null); // eslint-disable-line @typescript-eslint/no-explicit-any
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const speakText = useCallback((text: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const cleaned = text.replace(/\*\*/g, "").replace(/[#_`]/g, "");
    const utterance = new SpeechSynthesisUtterance(cleaned);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }, []);

  const startListening = useCallback(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || // eslint-disable-line @typescript-eslint/no-explicit-any
      (window as any).webkitSpeechRecognition; // eslint-disable-line @typescript-eslint/no-explicit-any
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
      const transcript = Array.from(event.results)
        .map((result: any) => result[0].transcript) // eslint-disable-line @typescript-eslint/no-explicit-any
        .join("");
      setInput(transcript);
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.start();
    recognitionRef.current = recognition;
    setIsListening(true);
  }, []);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const switchExpert = (e: (typeof EXPERTS)[0]) => {
    setExpert(e);
    setDropdownOpen(false);
    setMessages([
      {
        role: "assistant",
        content: `Expert switched. I'm now your **${e.label}** AI agent. I'll analyze your vest data through my specialized lens. What would you like to know?`,
      },
    ]);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsTyping(true);

    try {
      const r = await askAgent(expert.id, userMsg, patientId || undefined);
      const responseText = r.reply || "(no response)";
      setMessages((prev) => [...prev, { role: "assistant", content: responseText }]);
      speakText(responseText);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `_Agent unavailable — ${msg}._ Try again in a moment, or check the agent worker logs.` },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <>
      {!open && (
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-primary text-primary-foreground glow-cyan-strong flex items-center justify-center z-50 hover:scale-105 transition-transform cursor-pointer"
        >
          <MessageSquare className="w-6 h-6" />
        </motion.button>
      )}

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, x: 300 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 300 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed right-0 top-0 h-screen w-full sm:w-[400px] bg-card border-l border-border shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="bg-secondary p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Stethoscope className="w-5 h-5 text-primary" />
                <span className="font-display font-semibold text-secondary-foreground text-sm">
                  MedVerse Expert Console
                </span>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-secondary-foreground/60 hover:text-secondary-foreground transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Expert selector */}
            <div className="px-4 py-3 border-b border-border relative">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="w-full flex items-center justify-between bg-muted rounded-lg px-3 py-2 text-sm font-medium text-foreground hover:bg-muted/80 transition-colors cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <Bot className={`w-4 h-4 ${expert.color}`} />
                  {expert.label}
                </span>
                <ChevronDown
                  className={`w-4 h-4 transition-transform duration-200 ${
                    dropdownOpen ? "rotate-180" : ""
                  }`}
                />
              </button>

              <AnimatePresence>
                {dropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.15 }}
                    className="absolute left-4 right-4 top-full mt-1 bg-popover border border-border rounded-lg shadow-lg z-10 overflow-hidden"
                  >
                    {EXPERTS.map((e) => (
                      <button
                        key={e.id}
                        onClick={() => switchExpert(e)}
                        className={`w-full text-left px-3 py-2.5 text-sm flex items-center gap-2 hover:bg-muted transition-colors cursor-pointer ${
                          e.id === expert.id
                            ? "bg-muted font-medium"
                            : "text-foreground"
                        }`}
                      >
                        <Bot className={`w-4 h-4 ${e.color}`} />
                        {e.label}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className={`flex gap-2.5 ${
                    msg.role === "user" ? "flex-row-reverse" : ""
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 ${
                      msg.role === "assistant" ? "bg-primary/10" : "bg-secondary"
                    }`}
                  >
                    {msg.role === "assistant" ? (
                      <Bot className={`w-4 h-4 ${expert.color}`} />
                    ) : (
                      <User className="w-4 h-4 text-secondary-foreground" />
                    )}
                  </div>
                  <div
                    className={`max-w-[85%] rounded-lg px-3 py-2.5 text-sm leading-relaxed ${
                      msg.role === "assistant"
                        ? "bg-muted text-foreground"
                        : "bg-secondary text-secondary-foreground"
                    }`}
                  >
                    <div className="prose prose-sm max-w-none prose-invert [&>p]:m-0 [&>p]:text-inherit [&_strong]:text-inherit">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                    {msg.role === "assistant" && (
                      <button
                        onClick={() => speakText(msg.content)}
                        className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground hover:text-primary transition-colors cursor-pointer"
                      >
                        <Volume2 className="w-3 h-3" />
                        <span>Listen</span>
                      </button>
                    )}
                  </div>
                </motion.div>
              ))}
              {isTyping && (
                <div className="flex gap-2.5">
                  <div className="w-7 h-7 rounded-md bg-primary/10 flex items-center justify-center">
                    <Bot className={`w-4 h-4 ${expert.color}`} />
                  </div>
                  <div className="bg-muted rounded-lg px-3 py-2.5">
                    <div className="flex gap-1">
                      <span
                        className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce"
                        style={{ animationDelay: "0ms" }}
                      />
                      <span
                        className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce"
                        style={{ animationDelay: "150ms" }}
                      />
                      <span
                        className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce"
                        style={{ animationDelay: "300ms" }}
                      />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-border">
              {isListening && (
                <div className="mb-3 flex items-center justify-center gap-2 py-2">
                  <div className="flex items-center gap-1">
                    {[...Array(5)].map((_, i) => (
                      <motion.div
                        key={i}
                        animate={{ height: [4, 16, 4] }}
                        transition={{
                          duration: 0.5,
                          repeat: Infinity,
                          delay: i * 0.1,
                        }}
                        className="w-1 rounded-full bg-primary"
                      />
                    ))}
                  </div>
                  <span className="text-xs text-primary font-medium">
                    Listening...
                  </span>
                </div>
              )}
              {isSpeaking && (
                <div className="mb-3 flex items-center justify-center gap-2 py-1">
                  <Volume2 className="w-4 h-4 text-primary animate-pulse" />
                  <span className="text-xs text-primary font-medium">
                    Speaking...
                  </span>
                </div>
              )}
              <div className="flex gap-2">
                <button
                  onClick={isListening ? stopListening : startListening}
                  className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200 cursor-pointer ${
                    isListening
                      ? "bg-destructive text-destructive-foreground shadow-lg"
                      : "bg-muted text-muted-foreground hover:text-primary hover:bg-primary/10"
                  }`}
                >
                  {isListening ? (
                    <MicOff className="w-4 h-4" />
                  ) : (
                    <Mic className="w-4 h-4" />
                  )}
                </button>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  placeholder={`Ask your ${expert.label}...`}
                  className="flex-1 bg-muted rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-primary transition-shadow"
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim()}
                  className="w-10 h-10 rounded-lg bg-primary text-primary-foreground flex items-center justify-center disabled:opacity-40 hover:glow-cyan transition-all duration-200 cursor-pointer"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
