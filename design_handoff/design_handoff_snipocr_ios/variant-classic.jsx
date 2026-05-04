// variant-classic.jsx — Variant 1 (보수적): iPad NavigationSplitView
// 좌측: 토글 [원본 / 결과] + 히스토리 리스트 (고정).
// 우측: 토글 상태에 따라 [원본 캡처 뷰어] 또는 [OCR 결과 + 번역] 전환.
// "+ 새 OCR" 버튼은 툴바 우측 끝에 prominent 단일 CTA.

function VariantClassic({ tweaks }) {
  const [selected, setSelected] = React.useState(1);
  const [showLangMenu, setShowLangMenu] = React.useState(false);
  const [toast, setToast] = React.useState(null);
  const [showSheet, setShowSheet] = React.useState(false);
  const [reocr, setReocr] = React.useState(false);
  const [lang, setLang] = React.useState("영어");
  const [view, setView] = React.useState("result"); // "source" | "result"
  const tint = tweaks.tint;
  const showLabels = tweaks.toolbarDensity !== "icons";
  const transPos = tweaks.translationPos;

  function copy() {
    setToast({ text: "텍스트가 클립보드에 복사됨" });
    setTimeout(() => setToast(null), 1800);
  }
  function save() {
    setToast({ text: "텍스트 저장됨" });
    setTimeout(() => setToast(null), 1800);
  }
  function doReocr() {
    setReocr(true);
    setTimeout(() => setReocr(false), 1500);
  }

  const ToolBtn = ({ icon, label, onClick, danger }) => (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: showLabels ? 6 : 0,
      padding: showLabels ? "8px 12px" : "8px 10px",
      borderRadius: 10, border: "none",
      background: "transparent",
      color: danger ? "var(--sys-red)" : tint,
      font: "590 14px/1 var(--font-sf)",
      letterSpacing: "-0.24px",
      cursor: "pointer",
      whiteSpace: "nowrap", flexShrink: 0,
      transition: "background .15s, opacity .1s",
    }}
    onMouseEnter={(e) => e.currentTarget.style.background = "rgba(120,120,128,.10)"}
    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
      {icon}
      {showLabels && <span style={{whiteSpace:"nowrap"}}>{label}</span>}
    </button>
  );

  const tBgImage = tweaks.background === "wallpaper" ? "url('assets/ipad-light.jpg')" : "none";
  const tBgColor = tweaks.background === "solid" ? "#eef0f4"
                 : tweaks.background === "gradient" ? "linear-gradient(135deg, #e8eef7 0%, #f3e8ee 50%, #fef3e6 100%)"
                 : "#000";

  return (
    <div style={{
      width: 1180, height: 820, borderRadius: 38, overflow: "hidden",
      position: "relative",
      background: tBgImage !== "none" ? `${tBgImage} center/cover` : tBgColor,
      backgroundImage: tBgImage !== "none" ? tBgImage : tBgColor,
      backgroundSize: "cover",
      backgroundPosition: "center",
      boxShadow: "0 0 0 4px #000, 0 30px 80px rgba(0,0,0,.25)",
      padding: 14, boxSizing: "border-box",
    }}>
      <div style={{
        position: "relative", width: "100%", height: "100%",
        borderRadius: 28, overflow: "hidden",
        background: tBgImage !== "none" ? `url('assets/ipad-light.jpg') center/cover` : tBgColor,
      }}>
        {/* Status bar */}
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, height: 28, zIndex: 50,
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "6px 22px 0", color: "#000",
          font: "600 14px/1 var(--font-sf)", pointerEvents: "none",
        }}>
          <div>SnipOCR</div>
          <div>9:41</div>
          <div style={{display:"flex",alignItems:"center",gap:6}}>
            <span style={{fontSize:13}}>100%</span>
            <div style={{width:24,height:11,border:"1px solid currentColor",borderRadius:3,padding:1,boxSizing:"border-box",position:"relative",opacity:.85}}>
              <div style={{height:"100%",background:"currentColor",borderRadius:1,width:"90%"}}/>
              <div style={{position:"absolute",right:-3,top:3,width:2,height:5,background:"currentColor",borderRadius:"0 1px 1px 0"}}/>
            </div>
          </div>
        </div>

        {/* MAIN: left pane + detail */}
        <div style={{position:"absolute",inset:"36px 0 0",display:"flex"}}>
          {/* LEFT PANE — 토글 + 히스토리 리스트 (고정) */}
          <LeftPane
            view={view} onViewChange={setView}
            selected={selected} onSelect={setSelected}
            tint={tint}
          />

          {/* DETAIL */}
          <div style={{flex:1, position:"relative", display:"flex", flexDirection:"column",
                       background: "rgba(255,255,255,0.55)",
                       backdropFilter: "saturate(180%) blur(40px)",
                       WebkitBackdropFilter: "saturate(180%) blur(40px)"}}>
            {/* Floating glass toolbar */}
            <div style={{
              position: "absolute", top: 16, left: 20, right: 20, zIndex: 10,
              display: "flex", alignItems: "center", gap: 4,
              padding: 6, borderRadius: 14,
              background: "rgba(255,255,255,0.72)",
              backdropFilter: "saturate(180%) blur(40px)",
              WebkitBackdropFilter: "saturate(180%) blur(40px)",
              border: "0.5px solid rgba(255,255,255,0.6)",
              boxShadow: "0 8px 30px rgba(0,0,0,.10)",
            }}>
              <div style={{display:"flex",flexDirection:"column",lineHeight:1.1,paddingLeft:6,paddingRight:10,minWidth:0,flexShrink:1,overflow:"hidden"}}>
                <div style={{font:"600 14px/1.1 var(--font-sf)",letterSpacing:"-0.24px",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>호르무즈 해협 보도</div>
                <div className="footnote" style={{marginTop:2,whiteSpace:"nowrap"}}>방금 전 · 한국어</div>
              </div>
              <div style={{flex:1}}/>
              {view === "result" ? (
                <>
                  <ToolBtn icon={<SF.Copy size={17}/>} label="복사" onClick={copy}/>
                  <ToolBtn icon={<SF.DocText size={17}/>} label="저장" onClick={save}/>
                  <ToolBtn icon={<SF.Photo size={17}/>} label="이미지" onClick={save}/>
                  <ToolBtn icon={<SF.Redo size={17}/>} label="다시 OCR" onClick={doReocr}/>
                  <div style={{width:1,alignSelf:"stretch",margin:"6px 4px",background:"rgba(60,60,67,.18)"}}/>
                  <ToolBtn icon={<SF.Translate size={17}/>} label="번역" onClick={()=>{}}/>
                  {/* Lang pulldown */}
                  <div style={{position:"relative"}}>
                    <button onClick={()=>setShowLangMenu(s=>!s)} style={{
                      display:"flex",alignItems:"center",gap:6,
                      padding:"8px 11px", borderRadius:10, border:"none",
                      background:"rgba(120,120,128,.12)", color:"var(--label)",
                      font:"500 14px/1 var(--font-sf)", cursor:"pointer",
                      whiteSpace:"nowrap", flexShrink:0,
                    }}>
                      <SF.Globe size={14}/>
                      <span style={{whiteSpace:"nowrap"}}>{lang}</span>
                      <SF.ChevDn size={9}/>
                    </button>
                    {showLangMenu && (
                      <div style={{
                        position:"absolute", top:42, right:0, minWidth:180, padding:6,
                        borderRadius:14, zIndex:30,
                        background:"rgba(245,245,247,0.85)",
                        backdropFilter:"saturate(180%) blur(40px)",
                        WebkitBackdropFilter:"saturate(180%) blur(40px)",
                        border:"0.5px solid rgba(255,255,255,0.6)",
                        boxShadow:"0 12px 40px rgba(0,0,0,.18)",
                      }}>
                        {["영어","일본어","중국어 (간체)","스페인어","프랑스어"].map(L => (
                          <div key={L} onClick={()=>{setLang(L);setShowLangMenu(false);}}
                               style={{display:"flex",alignItems:"center",justifyContent:"space-between",
                                       padding:"8px 12px",borderRadius:8,cursor:"pointer",
                                       font:"400 15px/1 var(--font-sf)",
                                       background: lang===L?"rgba(0,0,0,.04)":"transparent"}}>
                            <span>{L}</span>
                            {lang===L && <span style={{color:tint}}><SF.Check size={15}/></span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <ToolBtn icon={<SF.Crop size={17}/>} label="영역 조정" onClick={()=>{}}/>
                  <ToolBtn icon={<SF.Photo size={17}/>} label="원본 보기" onClick={()=>{}}/>
                  <ToolBtn icon={<SF.Redo size={17}/>} label="다시 OCR" onClick={doReocr}/>
                  <div style={{width:1,alignSelf:"stretch",margin:"6px 4px",background:"rgba(60,60,67,.18)"}}/>
                  <ToolBtn icon={<SF.DocText size={17}/>} label="이미지 저장" onClick={save}/>
                </>
              )}
              {/* Prominent + 새 OCR CTA */}
              <button onClick={()=>setShowSheet(true)} style={{
                marginLeft:6,
                display:"flex",alignItems:"center",gap:6,
                padding:"0 14px 0 11px", height:40, borderRadius:12, border:"none",
                background: `linear-gradient(180deg, ${tint}, color-mix(in srgb, ${tint} 82%, black))`,
                color:"#fff",
                font:"700 15px/1 var(--font-sf)", letterSpacing:"-0.24px",
                whiteSpace:"nowrap", flexShrink:0,
                cursor:"pointer",
                boxShadow:`0 4px 14px ${tint}66, 0 0 0 0.5px color-mix(in srgb, ${tint} 60%, white) inset, 0 1px 0 rgba(255,255,255,.35) inset`,
                transition:"transform .12s, box-shadow .12s",
                animation: "ctaGlow 2.6s ease-in-out infinite",
              }}
              onMouseEnter={(e)=>{ e.currentTarget.style.transform="translateY(-1px)"; e.currentTarget.style.boxShadow=`0 8px 22px ${tint}88, 0 0 0 0.5px color-mix(in srgb, ${tint} 60%, white) inset, 0 1px 0 rgba(255,255,255,.35) inset`; }}
              onMouseLeave={(e)=>{ e.currentTarget.style.transform="translateY(0)"; e.currentTarget.style.boxShadow=`0 4px 14px ${tint}66, 0 0 0 0.5px color-mix(in srgb, ${tint} 60%, white) inset, 0 1px 0 rgba(255,255,255,.35) inset`; }}
              onMouseDown={(e)=>e.currentTarget.style.transform="translateY(0) scale(0.97)"}
              onMouseUp={(e)=>e.currentTarget.style.transform="translateY(-1px)"}>
                <SF.Plus size={18} weight={2.6}/>
                <span style={{whiteSpace:"nowrap"}}>새 OCR</span>
              </button>
            </div>

            {/* Content area */}
            <div style={{flex:1,marginTop:74,display:"flex",
                         flexDirection: transPos==="right"?"row":"column",
                         gap:12, padding:"0 20px 20px", minHeight:0}}>
              {view === "result" ? (
                <>
                  <Pane title="OCR 결과" tint={tint} reocr={reocr}>
                    <div className="body" style={{whiteSpace:"pre-wrap",color:"var(--label)",lineHeight:1.55}}>
                      {KO_TEXT}
                    </div>
                  </Pane>
                  {transPos !== "sheet" && (
                    <Pane title={`번역 → ${lang}`} tint={tint} translation>
                      <div className="body" style={{whiteSpace:"pre-wrap",color:"var(--label)",lineHeight:1.55}}>
                        {EN_TEXT}
                      </div>
                    </Pane>
                  )}
                </>
              ) : (
                <SourceDetail tint={tint} reocr={reocr}/>
              )}
            </div>
          </div>
        </div>

        {/* New OCR sheet */}
        {showSheet && <NewOCRSheet onClose={()=>setShowSheet(false)} tint={tint}/>}

        {/* Translation sheet */}
        {transPos === "sheet" && view === "result" && (
          <TranslationSheet lang={lang} tint={tint}/>
        )}

        {/* Toast */}
        {toast && (
          <div style={{
            position:"absolute", left:"50%", bottom:32, transform:"translateX(-50%)", zIndex:40,
            display:"flex",alignItems:"center",gap:10,
            padding:"12px 20px", borderRadius:999,
            background:"rgba(28,28,30,0.85)", color:"#fff",
            backdropFilter:"saturate(180%) blur(40px)",
            WebkitBackdropFilter:"saturate(180%) blur(40px)",
            font:"500 15px/1 var(--font-sf)",
            boxShadow:"0 12px 40px rgba(0,0,0,.25)",
          }}>
            <span style={{color:"var(--sys-green)"}}><SF.Check size={17}/></span>
            {toast.text}
          </div>
        )}

        {/* Re-OCR overlay */}
        {reocr && (
          <div style={{position:"absolute",inset:0,background:"rgba(0,0,0,0.18)",zIndex:35,
                       display:"flex",alignItems:"center",justifyContent:"center"}}>
            <div style={{padding:"20px 28px",borderRadius:18,
                         background:"rgba(255,255,255,0.85)",
                         backdropFilter:"saturate(180%) blur(40px)",
                         WebkitBackdropFilter:"saturate(180%) blur(40px)",
                         border:"0.5px solid rgba(255,255,255,.6)",
                         display:"flex",alignItems:"center",gap:14,
                         boxShadow:"0 20px 60px rgba(0,0,0,.20)"}}>
              <div style={{width:24,height:24,borderRadius:"50%",
                           border:`3px solid ${tint}`, borderTopColor:"transparent",
                           animation:"spin .8s linear infinite"}}/>
              <span className="headline">다시 인식 중…</span>
            </div>
          </div>
        )}

        {/* Home indicator */}
        <div style={{position:"absolute",bottom:6,left:"50%",transform:"translateX(-50%)",
                     width:200,height:5,background:"#000",borderRadius:3,opacity:.35,zIndex:60}}/>
      </div>
    </div>
  );
}

// ─────────────────────── LEFT PANE: 토글 + 히스토리(고정) ───────────────────────
function LeftPane({ view, onViewChange, selected, onSelect, tint }) {
  return (
    <div style={{
      width: 270, padding: "8px 12px 12px", flexShrink:0,
      background: "rgba(242,242,247,0.72)",
      backdropFilter: "saturate(180%) blur(40px)",
      WebkitBackdropFilter: "saturate(180%) blur(40px)",
      borderRight: "0.5px solid var(--separator)",
      display: "flex", flexDirection: "column", gap: 8, boxSizing: "border-box",
    }}>
      <div style={{padding:"6px 6px 4px"}}>
        <div className="title-2">SnipOCR</div>
      </div>

      {/* Segmented toggle: 원본 / 결과 — 우측 패널 뷰 제어 */}
      <div style={{
        position:"relative", display:"flex", padding:3, borderRadius:10,
        background:"rgba(118,118,128,.18)",
      }}>
        <div style={{
          position:"absolute", top:3, bottom:3,
          left: view==="source" ? 3 : "50%",
          width:"calc(50% - 3px)",
          borderRadius:8,
          background:"#fff",
          boxShadow:"0 1px 3px rgba(0,0,0,.10), 0 0 0 0.5px rgba(0,0,0,.04)",
          transition:"left .2s cubic-bezier(.3,.7,.4,1)",
        }}/>
        {[
          {id:"source", label:"원본", icon:<SF.Photo size={14}/>},
          {id:"result", label:"결과", icon:<SF.DocText size={14}/>},
        ].map(t => (
          <button key={t.id} onClick={()=>onViewChange(t.id)} style={{
            flex:1, position:"relative", zIndex:1, border:"none", background:"transparent",
            padding:"7px 4px",
            display:"flex",alignItems:"center",justifyContent:"center",gap:5,
            font:`${view===t.id?"600":"500"} 13px/1 var(--font-sf)`,
            color: view===t.id ? "var(--label)" : "var(--label-secondary)",
            cursor:"pointer", letterSpacing:"-0.08px",
          }}>
            {t.icon}
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* 히스토리 리스트 (항상 표시) */}
      <HistoryList selected={selected} onSelect={onSelect} tint={tint}/>
    </div>
  );
}

// ─────────────────── 우측: 원본 캡처 디테일 뷰 ───────────────────
function SourceDetail({ tint, reocr }) {
  const [zoom, setZoom] = React.useState(100);
  return (
    <div style={{flex:1, display:"flex", flexDirection:"column", gap:10, minHeight:0,
                 opacity: reocr ? 0.4 : 1, transition:"opacity .3s"}}>
      {/* Header */}
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"6px 4px"}}>
        <div className="footnote" style={{color:"var(--label-secondary)",
                                          textTransform:"uppercase",letterSpacing:".06em",fontWeight:600,
                                          whiteSpace:"nowrap"}}>원본 캡처</div>
        <div style={{display:"flex",alignItems:"center",gap:4,
                     padding:3,borderRadius:8,background:"rgba(120,120,128,.14)"}}>
          <button onClick={()=>setZoom(z=>Math.max(50,z-10))} style={{
            border:"none",background:"transparent",cursor:"pointer",padding:"4px 8px",color:tint,
            font:"600 14px/1 var(--font-sf)"}}>−</button>
          <span style={{font:"500 12px/1 var(--font-sf)",color:"var(--label-secondary)",minWidth:36,textAlign:"center"}}>{zoom}%</span>
          <button onClick={()=>setZoom(z=>Math.min(200,z+10))} style={{
            border:"none",background:"transparent",cursor:"pointer",padding:"4px 8px",color:tint,
            font:"600 14px/1 var(--font-sf)"}}>+</button>
        </div>
      </div>

      {/* Canvas */}
      <div style={{flex:1, borderRadius:16, overflow:"hidden", position:"relative",
                   background: "repeating-conic-gradient(#f0f0f3 0 25%, #fafafc 0 50%) 0/24px 24px",
                   border:"0.5px solid rgba(60,60,67,.10)",
                   boxShadow:"0 1px 2px rgba(0,0,0,.04)",
                   display:"flex",alignItems:"center",justifyContent:"center",
                   padding:24, minHeight:0}}>
        {/* Faux captured screenshot */}
        <div style={{
          width: `${(zoom/100) * 720}px`,
          maxWidth:"100%", maxHeight:"100%",
          aspectRatio:"4/3",
          background:"#fff",
          borderRadius:8,
          boxShadow:"0 12px 30px rgba(0,0,0,.14), 0 0 0 1px rgba(0,0,0,.06)",
          position:"relative",
          overflow:"hidden",
          transition:"width .15s",
        }}>
          {/* Mock browser/article header */}
          <div style={{height:34,background:"#f5f5f7",borderBottom:"1px solid #e5e5ea",
                       display:"flex",alignItems:"center",gap:6,padding:"0 12px"}}>
            <div style={{width:8,height:8,borderRadius:"50%",background:"#ff5f57"}}/>
            <div style={{width:8,height:8,borderRadius:"50%",background:"#febc2e"}}/>
            <div style={{width:8,height:8,borderRadius:"50%",background:"#28c840"}}/>
            <div style={{flex:1,height:18,background:"#fff",borderRadius:4,marginLeft:10,
                         border:"1px solid #e5e5ea",
                         font:"400 9px/18px var(--font-sf)",color:"#999",padding:"0 8px",
                         overflow:"hidden",whiteSpace:"nowrap"}}>news.example.com/article</div>
          </div>
          {/* Mock article body */}
          <div style={{padding:"18px 24px",fontFamily:"-apple-system, sans-serif",
                       color:"#1a1a1a",position:"relative"}}>
            <div style={{font:"700 14px/1.3 var(--font-sf)",marginBottom:8}}>호르무즈 해협 美 군함 피격설…</div>
            <div style={{font:"400 9px/1.55 var(--font-sf)",color:"#444",marginBottom:6}}>
              미군이 민간 선박의 호르무즈 해협 탈출을 지원하는 호위 작전 '프로젝트 프리덤'을 개시한 가운데, 호르무즈 해협 인근에서 미 해군 함정이 이란군의 미사일 공격을 받았다는 주장이 제기됐습니다.
            </div>
            <div style={{font:"400 9px/1.55 var(--font-sf)",color:"#444",marginBottom:6}}>
              이란 반관영 파르스 통신은 현지 시간 4일 현지 소식통을 인용해, 이란 남부 자스크 인근 오만만 해역에서 미 해군 호위함 1척이 미사일 2발을 맞고 퇴각했다고 보도했습니다.
            </div>
            <div style={{font:"400 9px/1.55 var(--font-sf)",color:"#444",marginBottom:6}}>
              통신은 해당 군함은 항행과 선박 통행 규정을 위반한 채 호르무즈 해협 통과를 시도했다고 주장했습니다.
            </div>
            <div style={{font:"400 9px/1.55 var(--font-sf)",color:"#444"}}>
              이어 "미 군함이 이란 해군의 경고를 무시하고 기동을 강행한 직후 미사일 공격의 표적이 됐다"며 "이 군함은 미사일 2발을 맞았고 이에 따라 항행을 계속하지 못하고 기수를 돌려 퇴각했다"고 밝혔습니다.
            </div>

            {/* OCR detection boxes */}
            <DetectBox top={42} left={24} width={88} height={20} color={tint} confidence={99}/>
            <DetectBox top={70} left={24} width={92} height={50} color={tint} confidence={98}/>
            <DetectBox top={126} left={24} width={92} height={42} color={tint} confidence={97}/>
            <DetectBox top={174} left={24} width={92} height={26} color={tint} confidence={99}/>
            <DetectBox top={206} left={24} width={92} height={50} color={tint} confidence={96}/>
          </div>
        </div>
      </div>

      {/* Footer info bar */}
      <div style={{display:"flex",alignItems:"center",gap:14,
                   padding:"10px 14px", borderRadius:12,
                   background:"rgba(255,255,255,0.78)",
                   border:"0.5px solid rgba(60,60,67,.10)",
                   font:"500 13px/1 var(--font-sf)",color:"var(--label-secondary)"}}>
        <div style={{display:"flex",alignItems:"center",gap:5,color:tint,fontWeight:600}}>
          <SF.Sparkle size={13}/>
          <span>인식 정확도 98%</span>
        </div>
        <div style={{width:1,height:14,background:"rgba(60,60,67,.18)"}}/>
        <span>5개 영역 · 312 글자</span>
        <div style={{width:1,height:14,background:"rgba(60,60,67,.18)"}}/>
        <span>화면 캡처 1.png · 1024 × 768</span>
        <div style={{flex:1}}/>
        <span>방금 전</span>
      </div>
    </div>
  );
}

function DetectBox({ top, left, width, height, color, confidence }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div onMouseEnter={()=>setHover(true)} onMouseLeave={()=>setHover(false)}
         style={{
      position:"absolute",
      top:`${top}px`, left:`${left}%`, width:`${width}%`, height:`${height}px`,
      border:`1.5px solid ${color}`,
      background: hover ? `color-mix(in srgb, ${color} 18%, transparent)` : `color-mix(in srgb, ${color} 8%, transparent)`,
      borderRadius:3,
      cursor:"pointer",
      transition:"background .15s",
    }}>
      {hover && (
        <div style={{
          position:"absolute", top:-22, left:0,
          padding:"2px 6px", borderRadius:4,
          background:color, color:"#fff",
          font:"600 9px/1.2 var(--font-sf)",
          whiteSpace:"nowrap",
        }}>{confidence}%</div>
      )}
    </div>
  );
}

function HistoryList({ selected, onSelect, tint }) {
  return (
    <div style={{flex:1, display:"flex", flexDirection:"column", gap:2, minHeight:0, overflow:"auto"}}>
      <div style={{margin:"4px 4px 8px",
                   display:"flex",alignItems:"center",gap:6,
                   padding:"7px 10px",borderRadius:10,
                   background:"rgba(118,118,128,.12)"}}>
        <span style={{color:"var(--label-secondary)"}}><SF.Search size={14}/></span>
        <span style={{font:"400 15px/1 var(--font-sf)",color:"var(--placeholder-text)"}}>검색</span>
      </div>
      <div style={{font:"500 11px/1 var(--font-sf)",letterSpacing:".06em",
                   textTransform:"uppercase",color:"var(--label-secondary)",
                   padding:"2px 10px 6px"}}>최근 OCR</div>
      {HISTORY.map(h => {
        const sel = selected === h.id;
        return (
          <div key={h.id} onClick={()=>onSelect(h.id)} style={{
            padding:"8px 10px", borderRadius:8, cursor:"pointer",
            background: sel ? `color-mix(in srgb, ${tint} 14%, transparent)` : "transparent",
            color: sel ? tint : "var(--label)",
          }}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",gap:8}}>
              <div style={{font:"600 14px/1.2 var(--font-sf)",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{h.title}</div>
              <div className="caption-1" style={{color: sel?tint:"var(--label-secondary)",flexShrink:0,opacity:.8}}>{h.time}</div>
            </div>
            <div className="footnote" style={{marginTop:2,color: sel ? `color-mix(in srgb, ${tint} 75%, var(--label-secondary))` : "var(--label-secondary)",
                       overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{h.preview}</div>
            <div style={{marginTop:4,display:"flex",alignItems:"center",gap:5,
                         font:"500 11px/1 var(--font-sf)",
                         color: sel ? tint : "var(--label-secondary)"}}>
              <SF.Globe size={11}/>
              <span>{h.lang}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Pane({ title, children, tint, translation, reocr }) {
  return (
    <div style={{flex:1, display:"flex", flexDirection:"column", minHeight:0, minWidth:0}}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"6px 4px"}}>
        <div className="footnote" style={{
          color: translation ? tint : "var(--label-secondary)",
          textTransform:"uppercase",letterSpacing:".06em",fontWeight:600,
          whiteSpace:"nowrap",
        }}>{title}</div>
        <div style={{display:"flex",alignItems:"center",gap:6,color:"var(--label-tertiary)"}}>
          <SF.Star size={13}/>
          <SF.Trash size={13}/>
        </div>
      </div>
      <div style={{
        flex:1, padding:"18px 22px", borderRadius:16,
        background: "rgba(255,255,255,0.85)",
        border:"0.5px solid rgba(60,60,67,0.10)",
        boxShadow:"0 1px 2px rgba(0,0,0,.04)",
        overflow:"auto", minHeight:0,
        opacity: reocr ? 0.4 : 1,
        transition: "opacity .3s",
      }}>
        {children}
      </div>
    </div>
  );
}

function NewOCRSheet({ onClose, tint }) {
  return (
    <div style={{position:"absolute",inset:0,background:"rgba(0,0,0,0.35)",zIndex:50,
                 display:"flex",alignItems:"flex-end",justifyContent:"center"}}
         onClick={onClose}>
      <div onClick={e=>e.stopPropagation()} style={{
        width:560, marginBottom:60, padding:"22px 22px 18px",
        borderRadius:22, background:"rgba(250,250,252,0.92)",
        backdropFilter:"saturate(180%) blur(40px)",
        WebkitBackdropFilter:"saturate(180%) blur(40px)",
        boxShadow:"0 30px 80px rgba(0,0,0,.30)",
      }}>
        <div style={{width:36,height:5,borderRadius:3,background:"var(--label-tertiary)",margin:"0 auto 18px"}}/>
        <div className="title-2" style={{textAlign:"center",marginBottom:6}}>새 OCR</div>
        <div className="footnote" style={{textAlign:"center",marginBottom:18}}>인식할 영역 또는 파일을 선택하세요</div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10}}>
          {[
            {icon:<SF.Crop size={28}/>, label:"화면 캡처", sub:"⌘⇧4"},
            {icon:<SF.Photo size={28}/>, label:"파일에서", sub:"이미지·PDF"},
            {icon:<SF.Scan size={28}/>, label:"카메라", sub:"연결된 기기"},
          ].map(o => (
            <button key={o.label} onClick={onClose} style={{
              padding:"22px 12px",borderRadius:14,border:"none",
              background:"rgba(118,118,128,.10)", color:"var(--label)",
              display:"flex",flexDirection:"column",alignItems:"center",gap:8,cursor:"pointer",
            }}>
              <span style={{color:tint}}>{o.icon}</span>
              <div style={{font:"600 15px/1 var(--font-sf)"}}>{o.label}</div>
              <div className="caption-1">{o.sub}</div>
            </button>
          ))}
        </div>
        <button onClick={onClose} style={{
          marginTop:14, width:"100%", padding:"14px",
          borderRadius:14, border:"none",
          background:"rgba(118,118,128,.16)", color:"var(--label)",
          font:"600 17px/1 var(--font-sf)", cursor:"pointer",
        }}>취소</button>
      </div>
    </div>
  );
}

function TranslationSheet({ lang, tint }) {
  return (
    <div style={{position:"absolute",left:60,right:60,bottom:24,
                 padding:18,borderRadius:18,zIndex:20,
                 background:"rgba(255,255,255,0.78)",
                 backdropFilter:"saturate(180%) blur(40px)",
                 WebkitBackdropFilter:"saturate(180%) blur(40px)",
                 border:"0.5px solid rgba(255,255,255,.6)",
                 boxShadow:"0 12px 40px rgba(0,0,0,.18)",
                 maxHeight:200, overflow:"auto"}}>
      <div className="footnote" style={{color:tint,fontWeight:600,marginBottom:8,textTransform:"uppercase",letterSpacing:".06em"}}>번역 → {lang}</div>
      <div className="body" style={{whiteSpace:"pre-wrap",lineHeight:1.55}}>{EN_TEXT}</div>
    </div>
  );
}

Object.assign(window, { VariantClassic });
