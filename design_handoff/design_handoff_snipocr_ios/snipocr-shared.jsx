// snipocr-shared.jsx — shared sample data + SF Symbols-style icons for all three variants

const KO_TEXT = `미군이 민간 선박의 호르무즈 해협 탈출을 지원하는 호위 작전 '프로젝트 프리덤'을 개시한 가운데,
호르무즈 해협 인근에서 미 해군 함정이 이란군의 미사일 공격을 받았다는 주장이 제기됐습니다.

이란 반관영 파르스 통신은 현지 시간 4일 현지 소식통을 인용해, 이란 남부 자스크 인근 오만만 해역에서 미 해군 호위함 1척이 미사일 2발을 맞고 퇴각했다고 보도했습니다.

통신은 해당 군함은 항행과 선박 통행 규정을 위반한 채 호르무즈 해협 통과를 시도했다고 주장했습니다.

이어 "미 군함이 이란 해군의 경고를 무시하고 기동을 강행한 직후 미사일 공격의 표적이 됐다"며 "이 군함은 미사일 2발을 맞았고 이에 따라 항행을 계속하지 못하고 기수를 돌려 퇴각했다"고 밝혔습니다.

이란 국영방송도 군 공보부를 인용해 "이란군의 신속하고 단호한 경고로 미 해군 '구축함들'의 호르무즈 해협 진입 시도가 저지됐다"고 전했습니다.

앞서 미군은 이날 오전부터 페르시아만에 체류 중인 민간 선박들의 안전한 이탈을 지원하기 위해 군함이 호위에 나서는 '프로젝트 프리덤' 작전을 시작했습니다.

이에 대해서 미군 중부사령부는 "피격된 미 함정은 없다"며 이란의 주장을 반박했습니다.`;

const EN_TEXT = `While the U.S. military has launched the escort operation 'Prosict Freedom' to support civilian ships escaping the Strait of Hormuz, there are claims that U.S. Navy ships are being attacked by Iranian missiles near the Strait of Hormuz.

Iran's semi-official Fars news agency cited local sources on the 4th local time as saying that a US Navy frigate was hit by two missiles and retreated from the sea near the Gulf of Oman near Jask, in the southeastern part of the country.

The news agency claimed that the warship attempted to transit the Strait of Hormuz in violation of navigation and ship traffic regulations.

He continued, "The U.S. warship ignored the Iranian Navy's warning and went ahead with the maneuver, immediately becoming the target of a missile attack," and "The warship was hit by two missiles and was forced to turn around and retreat."

Iran's state broadcaster also cited the military's public affairs department, saying, "The Iranian Navy's swift and resolute warning thwarted the U.S. Navy's 'destroyers' attempts to enter the Strait of Hormuz."

Earlier, the U.S. military launched 'Project Freedom', an escort operation to support the safe departure of civilian ships in the Persian Gulf, starting that morning.

In response, U.S. Central Command refuted Iran's claim, saying, "No U.S. ships were hit."`;

const HISTORY = [
  { id: 1, title: "호르무즈 해협 보도", time: "방금 전", preview: "미군이 민간 선박의 호르무즈 해협…", lang: "한 → 영", active: true },
  { id: 2, title: "PDF 5페이지 발췌", time: "10분 전", preview: "Apple Vision Pro의 새로운 기능은…", lang: "영 → 한" },
  { id: 3, title: "스크린샷 발표자료", time: "어제", preview: "2026년 1분기 실적은 전년 동기 대비…", lang: "복사만" },
  { id: 4, title: "약 처방 라벨", time: "어제", preview: "1일 3회, 식후 30분 이내에 복용…", lang: "한 → 영" },
  { id: 5, title: "메뉴판 일본어", time: "월요일", preview: "本日のおすすめは新鮮な…", lang: "일 → 한" },
];

// SF Symbol-ish glyphs (stroke-based, weight 2)
const SF = {
  Plus:    (p) => <svg width={p.size||22} height={p.size||22} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={p.weight||2.2} strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>,
  Copy:    (p) => <svg width={p.size||20} height={p.size||20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="11" height="11" rx="2.5"/><path d="M15 5H6a2 2 0 00-2 2v9"/></svg>,
  DocText: (p) => <svg width={p.size||20} height={p.size||20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M14 3H6a2 2 0 00-2 2v14a2 2 0 002 2h12a2 2 0 002-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h6"/></svg>,
  Photo:   (p) => <svg width={p.size||20} height={p.size||20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="14" rx="2.5"/><circle cx="9" cy="11" r="1.6"/><path d="M3 17l5-5 4 4 3-3 6 6"/></svg>,
  Redo:    (p) => <svg width={p.size||20} height={p.size||20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M21 7v6h-6"/><path d="M21 13a9 9 0 11-3-6.7L21 7"/></svg>,
  Translate:(p)=> <svg width={p.size||20} height={p.size||20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 5h11M9 3v2"/><path d="M11 5c-.5 5-3 9-7 11M7 8c1 3 3.5 5.5 7 7"/><path d="M13 21l4.5-11 4.5 11M14.5 17h6"/></svg>,
  Globe:   (p) => <svg width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18"/></svg>,
  Search:  (p) => <svg width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>,
  Chevron: (p) => <svg width={p.size||10} height={(p.size||10)*1.5} viewBox="0 0 8 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 2l4 4-4 4"/></svg>,
  ChevDn:  (p) => <svg width={p.size||10} height={p.size||10} viewBox="0 0 12 8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 2l4 4 4-4"/></svg>,
  Check:   (p) => <svg width={p.size||16} height={p.size||16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7"/></svg>,
  Close:   (p) => <svg width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>,
  Crop:    (p) => <svg width={p.size||40} height={p.size||40} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2v16a2 2 0 002 2h14"/><path d="M2 6h16a2 2 0 012 2v14"/></svg>,
  Sparkle: (p) => <svg width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></svg>,
  Sidebar: (p) => <svg width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>,
  Clock:   (p) => <svg width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>,
  Trash:   (p) => <svg width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M9 6V4a2 2 0 012-2h2a2 2 0 012 2v2"/></svg>,
  Star:    (p) => <svg width={p.size||16} height={p.size||16} viewBox="0 0 24 24" fill={p.filled?"currentColor":"none"} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l3 6 6.5.9-4.7 4.6 1.1 6.5L12 18l-5.9 3 1.1-6.5L2.5 9.9 9 9z"/></svg>,
  Settings:(p) => <svg width={p.size||18} height={p.size||18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.6 1.6 0 00-1.8-.3 1.6 1.6 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.6 1.6 0 00-1-1.5 1.6 1.6 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.6 1.6 0 00.3-1.8 1.6 1.6 0 00-1.5-1H3a2 2 0 110-4h.1a1.6 1.6 0 001.5-1 1.6 1.6 0 00-.3-1.8l-.1-.1A2 2 0 117 4.6l.1.1a1.6 1.6 0 001.8.3H9a1.6 1.6 0 001-1.5V3a2 2 0 114 0v.1a1.6 1.6 0 001 1.5 1.6 1.6 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.6 1.6 0 00-.3 1.8V9a1.6 1.6 0 001.5 1H21a2 2 0 110 4h-.1a1.6 1.6 0 00-1.5 1z"/></svg>,
  Scan:    (p) => <svg width={p.size||22} height={p.size||22} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7V5a2 2 0 012-2h2M21 7V5a2 2 0 00-2-2h-2M3 17v2a2 2 0 002 2h2M21 17v2a2 2 0 01-2 2h-2M3 12h18"/></svg>,
};

Object.assign(window, { KO_TEXT, EN_TEXT, HISTORY, SF });
