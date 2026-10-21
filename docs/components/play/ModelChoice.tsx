'use client';

import { useEffect, useState } from 'react';
import { activeModelAsset } from '@/lib/play/model-asset';
import { withBasePath } from '@/lib/site';

export default function ModelChoice({ lobby }: { lobby: boolean }) {
  const [model, setModel] = useState<ReturnType<typeof activeModelAsset> | null>(null);
  useEffect(() => { setModel(activeModelAsset()); }, []);
  if (!model) return null;
  return <div dir="rtl" className="shrink-0 px-4 py-2 text-xs space-y-2" aria-label="نسخة Otter الحالية">
    <p className="font-semibold">{model.label}</p>
    {lobby && <>
      <p>اختر النسخة لبدء جلسة جديدة:</p>
      <div className="flex flex-wrap gap-4">
        <a className="underline" href={withBasePath('/play/')} aria-current={model.id === 'original' ? 'page' : undefined}>الأصلي</a>
        <a className="underline" href={`${withBasePath('/play/')}?model=trained`} aria-current={model.id === 'trained' ? 'page' : undefined}>المتدرّب على 3+0</a>
      </div>
      {model.id === 'trained' && <p>تدريب إضافي على نقلات البشر. التفوّق في القوة على الأصلي لم يثبت. <a className="underline" href={withBasePath('/training/')}>نتائج الاختبارات</a></p>}
    </>}
  </div>;
}
