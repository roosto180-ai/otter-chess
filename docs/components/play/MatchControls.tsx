'use client';
import { useState } from 'react';

export default function MatchControls({ ended, continueMode, notice, noLegalMoves, playerTime, otterTime, editClock, onContinue, onNewGame, onExport }: {
  ended: boolean; continueMode: boolean; notice: string; noLegalMoves: boolean;
  playerTime: number; otterTime: number;
  editClock: (side: 'player' | 'otter', seconds: number) => void;
  onContinue: () => void; onNewGame: () => void; onExport: () => void;
}) {
  const [minutes, setMinutes] = useState('5');
  const seconds = Number(minutes) * 60;
  const valid = minutes.trim() !== '' && Number.isFinite(seconds) && seconds >= 0 && seconds <= 86400;
  const btn = 'border border-pear/50 rounded px-2 py-1.5 text-xs cursor-pointer disabled:opacity-40';
  return <section dir="rtl" className="p-3 border-b border-line space-y-2 text-paper bg-panel/50 shrink-0" aria-label="الوقت والمتابعة">
    <strong className="text-sm">{continueMode ? 'وضع متابعة / تحليل — دون احتساب نتيجة' : ended ? 'انتهت المباراة — الموضع محفوظ' : 'ساعة قابلة للتعديل'}</strong>
    <p className="text-xs text-muted">نسخة مستقلة معدّلة من Peargent Labs Otter. تغيير الوقت يغيّر مدخل الوقت للنموذج؛ التصنيف والأوزان ثابتة.</p>
    <div className="flex flex-wrap gap-2 items-center">
      <label className="text-xs">الوقت بالدقائق <input aria-label="الوقت بالدقائق" className="bg-bg border border-line p-1 w-20" type="number" min="0" max="1440" step="0.1" value={minutes} onChange={e => setMinutes(e.target.value)} /></label>
      <button className={btn} disabled={!valid} onClick={() => editClock('player', seconds)}>تعيين وقتي</button>
      <button className={btn} onClick={() => editClock('player', 300)}>وقتي 5 دقائق</button>
      <button className={btn} disabled={!valid} onClick={() => editClock('otter', seconds)}>تعيين وقت Otter</button>
    </div>
    <p className="text-xs" aria-live="polite">وقتك: {Math.ceil(playerTime)} ث · Otter: {Math.ceil(otterTime)} ث</p>
    {(ended || noLegalMoves) && <button className={btn} onClick={onContinue}>{noLegalMoves ? 'تراجع إلى قرارك السابق وافتح فرع متابعة تحليلي' : 'متابعة من نفس الموضع — وضع تحليلي'}</button>}
    <p className="text-xs text-muted" role="status">{notice}</p>
    <div className="flex gap-2"><button className={btn} onClick={onExport}>عرض / نسخ PGN</button><button className={btn} onClick={onNewGame}>مباراة جديدة / القائمة</button></div>
  </section>;
}
