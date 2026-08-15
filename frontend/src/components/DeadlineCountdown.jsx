import React, { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';

export default function DeadlineCountdown({ deadlineIso }) {
  const [timeLeft, setTimeLeft] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0, isExpired: false });

  useEffect(() => {
    const calculateTime = () => {
      const now = new Date();
      const target = new Date(deadlineIso);
      const diff = target - now;

      if (diff <= 0) {
        setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0, isExpired: true });
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
      const minutes = Math.floor((diff / 1000 / 60) % 60);
      const seconds = Math.floor((diff / 1000) % 60);

      setTimeLeft({ days, hours, minutes, seconds, isExpired: false });
    };

    calculateTime();
    const interval = setInterval(calculateTime, 1000);
    return () => clearInterval(interval);
  }, [deadlineIso]);

  if (timeLeft.isExpired) {
    return (
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <Clock className="w-3.5 h-3.5" />
        <span>EXPIRED</span>
      </div>
    );
  }

  const isUrgent = timeLeft.days <= 15;

  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-medium ${
      isUrgent 
        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse' 
        : 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20'
    }`}>
      <Clock className="w-3.5 h-3.5" />
      <span>
        {timeLeft.days}d {timeLeft.hours}h {timeLeft.minutes}m {timeLeft.seconds}s
      </span>
    </div>
  );
}
