import base64, os

# Read logo
with open("C:/Vibe Code/00 Kodryx AI Design System/assets/logo-kodryx-white-bg.png", "rb") as f:
    logo_uri = "data:image/png;base64," + base64.b64encode(f.read()).decode()

L = logo_uri
LOGO = f'<img src="{L}" alt="Kodryx AI" style="height:26px;opacity:.8;" />'
LOGO_LG = f'<img src="{L}" alt="Kodryx AI" style="height:60px;" />'

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Kodryx AI — Healthcare Seed Deck</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--navy:#0E2A3A;--gold:#C9A24D;--gbg:rgba(201,162,77,.1);--grey:#6B7280;--g50:#F7F8FA;--g100:#EEF0F3;--g200:#D8DCE2;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:100%;height:100%;overflow:hidden;background:#D0D4DA;font-family:Inter,sans-serif;}}
#viewer{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;}}
#stage{{position:relative;width:1440px;height:810px;transform-origin:center center;}}
.slide{{position:absolute;inset:0;width:1440px;height:810px;opacity:0;pointer-events:none;transition:opacity .28s;background:#fff;overflow:hidden;}}
.slide.on{{opacity:1;pointer-events:all;}}
/* Nav */
#nav{{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:11px;background:rgba(14,42,58,.92);backdrop-filter:blur(14px);border-radius:32px;padding:8px 18px;z-index:999;}}
#nav button{{background:rgba(255,255,255,.12);border:none;border-radius:6px;color:#fff;font-size:15px;cursor:pointer;width:34px;height:28px;display:flex;align-items:center;justify-content:center;transition:background .15s;}}
#nav button:hover{{background:rgba(255,255,255,.22);}}
#nav button:disabled{{opacity:.22;cursor:default;}}
#ctr{{font-family:Inter;font-size:11px;font-weight:600;color:rgba(255,255,255,.5);min-width:44px;text-align:center;letter-spacing:.04em;}}
#dots{{display:flex;gap:5px;align-items:center;}}
.dot{{width:5px;height:5px;border-radius:50%;background:rgba(255,255,255,.22);cursor:pointer;transition:all .2s;}}
.dot.on{{background:#C9A24D;width:16px;border-radius:3px;}}
/* Shared */
.si{{width:100%;height:100%;display:flex;flex-direction:column;padding:56px 72px;position:relative;}}
.ey{{font-family:Inter;font-size:10px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;color:var(--grey);margin-bottom:6px;}}
.gr{{height:3px;width:48px;background:var(--gold);border:0;margin:14px 0 20px;}}
.sn{{position:absolute;bottom:26px;left:72px;font-family:Inter;font-size:10px;color:var(--grey);letter-spacing:.05em;}}
.fl{{position:absolute;bottom:22px;right:56px;}}
h2.tt{{font-family:Poppins;font-weight:700;font-size:38px;color:var(--navy);letter-spacing:-.015em;margin:4px 0 0;}}
.g{{color:var(--gold);}}
/* Cover */
.s1 .si{{padding:56px 72px;}}
.s1 .topbar{{display:flex;justify-content:space-between;align-items:center;}}
.s1 .badge{{background:var(--gbg);border:1px solid rgba(201,162,77,.3);border-radius:999px;padding:4px 14px;font-family:Inter;font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--gold);}}
.s1 h1{{font-family:Poppins;font-weight:800;font-size:76px;line-height:1.0;letter-spacing:-.025em;color:var(--navy);margin:40px 0 0;max-width:920px;}}
.s1 .sub{{font-family:Inter;font-size:18px;color:var(--grey);margin-top:20px;max-width:620px;line-height:1.55;}}
.s1 hr{{height:3px;width:64px;background:var(--gold);border:0;margin:28px 0;}}
.s1 .bot{{display:flex;justify-content:space-between;align-items:flex-end;position:absolute;bottom:52px;left:72px;right:72px;}}
.s1 .nm{{font-family:Poppins;font-weight:700;font-size:18px;color:var(--navy);}}
.s1 .nm small{{display:block;font-family:Inter;font-weight:400;font-size:13px;color:var(--grey);margin-top:2px;}}
.s1 .rais .dt{{font-family:Inter;font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--grey);}}
.s1 .rais .am{{font-family:Poppins;font-weight:700;font-size:24px;color:var(--navy);margin-top:2px;}}
/* Prob */
.s2 .pg{{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:16px;flex:1;}}
.s2 .pc{{background:var(--g50);border-radius:11px;padding:36px 26px;border-top:3px solid var(--gold);display:flex;flex-direction:column;gap:10px;}}
.s2 .ps{{font-family:Poppins;font-weight:800;font-size:62px;line-height:1;color:var(--navy);letter-spacing:-.02em;}}
.s2 .pl{{font-family:Poppins;font-weight:600;font-size:18px;color:var(--navy);line-height:1.3;}}
.s2 .pb{{font-family:Inter;font-size:13px;color:var(--grey);line-height:1.6;margin-top:2px;}}
/* Platform */
.s3 .pg{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:22px;flex:1;}}
.s3 .pc{{background:#fff;border:1px solid var(--g100);border-radius:11px;padding:32px 24px;display:flex;flex-direction:column;gap:9px;}}
.s3 .pi{{width:44px;height:44px;background:var(--gbg);border-radius:8px;display:flex;align-items:center;justify-content:center;}}
.s3 .pi svg{{width:22px;height:22px;color:var(--gold);}}
.s3 .pt{{font-family:Inter;font-size:10px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);}}
.s3 .pn{{font-family:Poppins;font-weight:700;font-size:22px;color:var(--navy);line-height:1.2;}}
.s3 .pd{{font-family:Inter;font-size:13px;color:var(--grey);line-height:1.6;}}
.s3 .pv{{font-family:Poppins;font-weight:700;font-size:24px;color:var(--gold);margin-top:auto;padding-top:12px;border-top:1px solid var(--g100);}}
.s3 .pvl{{font-family:Inter;font-size:11px;color:var(--grey);}}
/* Product detail (s4,s5,s6) */
.sprod .sp{{display:grid;grid-template-columns:1fr 1fr;gap:52px;margin-top:10px;flex:1;align-items:start;}}
.sprod .tg{{font-family:Poppins;font-weight:800;font-size:44px;line-height:1.05;color:var(--navy);letter-spacing:-.02em;margin-bottom:14px;}}
.sprod .dc{{font-family:Inter;font-size:15px;color:var(--grey);line-height:1.7;max-width:540px;}}
.sprod .mr{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:24px;}}
.sprod .mb{{background:var(--g50);border-radius:8px;padding:16px 12px;border-top:3px solid var(--gold);text-align:center;}}
.sprod .mv{{font-family:Poppins;font-weight:700;font-size:28px;color:var(--navy);letter-spacing:-.02em;}}
.sprod .ml{{font-family:Inter;font-size:11px;color:var(--grey);margin-top:2px;line-height:1.4;}}
.sprod .bl{{display:flex;flex-direction:column;gap:13px;margin-top:2px;}}
.sprod .bi{{display:flex;gap:10px;align-items:flex-start;}}
.sprod .bd{{width:6px;height:6px;background:var(--gold);border-radius:50%;margin-top:6px;flex-shrink:0;}}
.sprod .bt{{font-family:Inter;font-size:14px;color:var(--navy);line-height:1.5;}}
.sprod .bt strong{{font-weight:600;}}
.sprod .hb{{background:var(--navy);border-radius:9px;padding:20px 22px;margin-top:16px;}}
.sprod .hv{{font-family:Poppins;font-weight:800;font-size:36px;color:var(--gold);letter-spacing:-.02em;}}
.sprod .hl{{font-family:Inter;font-size:13px;color:rgba(255,255,255,.6);margin-top:2px;}}
/* Validation (s7) */
.s7 .vt{{width:100%;margin-top:16px;border-collapse:collapse;font-size:13px;}}
.s7 .vt th{{font-family:Inter;font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--grey);padding:11px 14px;text-align:left;border-bottom:2px solid var(--g100);}}
.s7 .vt td{{font-family:Inter;font-size:13px;color:var(--navy);padding:12px 14px;border-bottom:1px solid var(--g100);}}
.s7 .vt tr:last-child td{{border-bottom:none;}}
.s7 .vt .pc{{font-family:Poppins;font-weight:600;font-size:14px;}}
.s7 .vt .mv{{font-family:Poppins;font-weight:700;font-size:18px;color:var(--gold);}}
.s7 .vt .chip{{background:var(--gbg);border:1px solid rgba(201,162,77,.25);border-radius:999px;padding:2px 10px;font-family:Inter;font-size:10px;font-weight:600;color:var(--gold);display:inline-block;}}
.s7 .note{{background:var(--navy);border-radius:9px;padding:16px 22px;margin-top:14px;display:flex;gap:24px;align-items:center;}}
.s7 .note .ni{{font-family:Inter;font-size:12px;color:rgba(255,255,255,.65);}}
.s7 .note .ni strong{{color:var(--gold);font-weight:600;}}
/* Market (s8) */
.s8 .mg{{display:grid;grid-template-columns:1fr 1fr;gap:44px;margin-top:22px;flex:1;align-items:start;}}
.s8 .bs{{font-family:Poppins;font-weight:800;font-size:80px;line-height:1;color:var(--gold);letter-spacing:-.03em;}}
.s8 .bl{{font-family:Poppins;font-weight:600;font-size:19px;color:var(--navy);margin-top:5px;}}
.s8 .bss{{font-family:Inter;font-size:13px;color:var(--grey);margin-top:4px;}}
.s8 .mi{{display:flex;flex-direction:column;gap:14px;}}
.s8 .mc{{display:flex;gap:12px;align-items:flex-start;padding:16px 18px;background:var(--g50);border-radius:8px;border-left:3px solid var(--gold);}}
.s8 .mv{{font-family:Poppins;font-weight:700;font-size:22px;color:var(--navy);min-width:80px;}}
.s8 .md{{font-family:Inter;font-size:13px;color:var(--grey);line-height:1.5;}}
/* Traction (s9) */
.s9 .tg{{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:18px;}}
.s9 .tc{{background:var(--g50);border-radius:10px;padding:26px 22px;border-top:3px solid var(--gold);}}
.s9 .tp{{font-family:Inter;font-size:10px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);margin-bottom:5px;}}
.s9 .tv{{font-family:Poppins;font-weight:800;font-size:44px;color:var(--navy);letter-spacing:-.02em;line-height:1;}}
.s9 .tl{{font-family:Poppins;font-weight:600;font-size:16px;color:var(--navy);margin-top:5px;}}
.s9 .td{{font-family:Inter;font-size:12px;color:var(--grey);margin-top:4px;line-height:1.5;}}
.s9 .steps{{background:var(--navy);border-radius:9px;padding:20px 26px;margin-top:18px;display:grid;grid-template-columns:repeat(4,1fr);gap:16px;}}
.s9 .st{{}}
.s9 .sw{{font-family:Poppins;font-weight:700;font-size:14px;color:var(--gold);}}
.s9 .sd{{font-family:Inter;font-size:12px;color:rgba(255,255,255,.65);margin-top:3px;line-height:1.4;}}
.s9 .pb{{display:inline-flex;align-items:center;gap:7px;background:var(--gbg);border:1px solid rgba(201,162,77,.3);border-radius:999px;padding:6px 16px;font-family:Inter;font-size:12px;font-weight:600;color:var(--gold);margin-top:14px;}}
.s9 .pb .dot{{width:6px;height:6px;background:var(--gold);border-radius:50%;}}
/* Biz (s10) */
.s10 .bg{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:14px;}}
.s10 .bc{{background:#fff;border:1px solid var(--g100);border-radius:10px;padding:22px 18px;}}
.s10 .bh{{font-family:Poppins;font-weight:700;font-size:16px;color:var(--navy);margin-bottom:10px;}}
.s10 .bt2{{font-family:Inter;font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin-bottom:4px;}}
.s10 table{{width:100%;border-collapse:collapse;font-size:12px;}}
.s10 table th{{font-family:Inter;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--grey);padding:7px 10px;text-align:left;border-bottom:1px solid var(--g100);}}
.s10 table td{{font-family:Inter;font-size:12px;color:var(--navy);padding:8px 10px;border-bottom:1px solid var(--g100);}}
.s10 table tr:last-child td{{border-bottom:none;}}
.s10 table .mv{{font-family:Poppins;font-weight:700;font-size:14px;color:var(--gold);}}
.s10 .bb{{background:var(--navy);border-radius:9px;padding:18px 22px;margin-top:14px;}}
.s10 .bbt{{font-family:Poppins;font-weight:600;font-size:16px;color:#fff;}}
.s10 .bbt span{{color:var(--gold);}}
.s10 .bbn{{font-family:Inter;font-size:12px;color:rgba(255,255,255,.5);margin-top:3px;}}
/* Team (s11) */
.s11 .tg{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-top:22px;}}
.s11 .tc{{background:var(--g50);border-radius:10px;padding:22px 18px;border-top:3px solid var(--gold);}}
.s11 .av{{width:46px;height:46px;background:var(--navy);border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:Poppins;font-weight:700;font-size:17px;color:var(--gold);margin-bottom:10px;}}
.s11 .tn{{font-family:Poppins;font-weight:700;font-size:16px;color:var(--navy);}}
.s11 .tr{{font-family:Inter;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--gold);margin-top:3px;}}
.s11 .tb{{font-family:Inter;font-size:12px;color:var(--grey);margin-top:8px;line-height:1.5;}}
.s11 .cert{{background:var(--gbg);border:1px solid rgba(201,162,77,.25);border-radius:8px;padding:14px 18px;margin-top:18px;display:flex;gap:16px;align-items:center;}}
.s11 .cert-text{{font-family:Inter;font-size:12px;color:var(--navy);line-height:1.5;}}
.s11 .cert-text strong{{font-weight:600;color:var(--gold);}}
/* Ask (s12) */
.s12 .ab{{display:grid;grid-template-columns:1fr 1fr;gap:52px;margin-top:22px;flex:1;align-items:start;}}
.s12 .aa{{font-family:Poppins;font-weight:800;font-size:80px;color:var(--navy);line-height:1;letter-spacing:-.03em;}}
.s12 .al{{font-family:Inter;font-size:16px;color:var(--grey);margin-top:5px;}}
.s12 .au{{margin-top:22px;display:flex;flex-direction:column;gap:9px;}}
.s12 .ui{{display:flex;gap:9px;align-items:center;}}
.s12 .up{{font-family:Poppins;font-weight:700;font-size:20px;color:var(--gold);min-width:52px;}}
.s12 .ud{{font-family:Inter;font-size:13px;color:var(--navy);}}
.s12 .cb{{background:var(--navy);border-radius:11px;padding:32px 28px;}}
.s12 .ct{{font-family:Poppins;font-weight:700;font-size:19px;color:#fff;margin-bottom:18px;}}
.s12 .ci{{display:flex;gap:10px;align-items:center;margin-bottom:11px;}}
.s12 .ck{{font-family:Inter;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.38);min-width:72px;}}
.s12 .cv{{font-family:Inter;font-size:13px;color:#fff;}}
.s12 .cv a{{color:var(--gold);text-decoration:none;}}
.s12 .cta{{display:inline-block;margin-top:20px;background:var(--gold);color:var(--navy);font-family:Poppins;font-weight:700;font-size:14px;padding:12px 24px;border-radius:6px;text-decoration:none;}}
</style>
</head>
<body>
<div id="viewer"><div id="stage">

<!-- 1. COVER -->
<section class="slide s1 on">
  <div class="si">
    <div class="topbar">{LOGO_LG}<div class="badge">Seed Round &middot; 2026</div></div>
    <h1 style="font-family:Poppins;font-weight:800;font-size:76px;line-height:1.0;letter-spacing:-.025em;color:#0E2A3A;margin:40px 0 0;max-width:920px;">The AI Infrastructure<br/>for <span class="g">Healthcare.</span></h1>
    <p style="font-family:Inter;font-size:18px;color:#6B7280;margin-top:18px;max-width:640px;line-height:1.55;">Clinically validated AI across radiology, wound care, and dental diagnostics. Deployed in India&rsquo;s most under-served markets. DPIIT certified.</p>
    <p style="font-family:Poppins;font-weight:600;font-size:18px;color:#C9A24D;margin-top:14px;letter-spacing:.04em;">Intelligence. Innovation. Impact.</p>
    <hr style="height:3px;width:64px;background:#C9A24D;border:0;margin:28px 0;" />
    <div class="bot">
      <div><div class="nm">Sonu Kumar<small>Founder &amp; CEO &middot; Kodryx AI</small></div></div>
      <div class="rais" style="text-align:right;">
        <div class="dt">Q2 &middot; 2026</div>
        <div class="am">Raising <span class="g">$3M</span> Seed</div>
      </div>
    </div>
  </div>
</section>

<!-- 2. THE PROBLEM -->
<section class="slide s2">
  <div class="si">
    <div class="ey">The Crisis</div>
    <h2 class="tt">A triple crisis in care delivery.</h2>
    <hr class="gr" />
    <div class="pg">
      <div class="pc">
        <div class="ps"><span class="g">1</span>-in-6</div>
        <div class="pl">The Amputation Crisis</div>
        <div class="pb">India is the diabetes capital of the world. 1 in 6 adults affected. 20% of diabetic foot ulcers progress to amputation. Annual burden: &#8377;30K&ndash;&#8377;2L per patient. Avoidable with early AI-powered assessment.</div>
      </div>
      <div class="pc">
        <div class="ps">1:<span class="g">100K</span></div>
        <div class="pl">The Radiologist Shortage</div>
        <div class="pb">Specialist access is non-existent in Tier 2/3 cities. Experts are trapped in a &ldquo;linear bottleneck&rdquo; of manual data entry. Acute burnout and delayed intervention are systemic outcomes.</div>
      </div>
      <div class="pc">
        <div class="ps"><span class="g">1</span>-in-4</div>
        <div class="pl">The Diagnostic Blockade</div>
        <div class="pb">25% of strokes are missed on initial imaging reads. Analog intake forms require a full-time human resource just to transcribe data. Manual workflows are not just slow &mdash; they are a primary margin killer.</div>
      </div>
    </div>
    <div class="sn">02</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 3. PLATFORM OVERVIEW -->
<section class="slide s3">
  <div class="si">
    <div class="ey">The Solution</div>
    <h2 class="tt">Three clinically validated AI products. One infrastructure layer.</h2>
    <hr class="gr" />
    <div class="pg">
      <div class="pc">
        <div class="pi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg></div>
        <div class="pt">Multi-Modality Diagnostics</div>
        <div class="pn">Radiology<br/>AI Agent</div>
        <div class="pd">High-velocity findings engine for CT, MRI, and X-ray. Agentic workflow automation with patient chart review integration.</div>
        <div class="pv">60%</div>
        <div class="pvl">Faster reporting turnaround</div>
      </div>
      <div class="pc">
        <div class="pi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 0 1 10 10"/><circle cx="12" cy="12" r="3"/><path d="M12 6v6l4 2"/></svg></div>
        <div class="pt">Wound Intelligence</div>
        <div class="pn">WIDAS</div>
        <div class="pd">Proprietary DFU classification and healing prediction system. Democratizes expert-level wound care across Tier 2/3 cities.</div>
        <div class="pv">&gt;94%</div>
        <div class="pvl">AI classification accuracy</div>
      </div>
      <div class="pc">
        <div class="pi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6M9 12h6M9 15h4"/></svg></div>
        <div class="pt">Dental Radiology AI</div>
        <div class="pn">CBCT<br/>STRUCT</div>
        <div class="pd">AI-powered structuring to eradicate turnaround delays. Three-sector architecture: pre-analysis, clinical core, one-click delivery.</div>
        <div class="pv">5&times;</div>
        <div class="pvl">Faster diagnostic prep</div>
      </div>
    </div>
    <div class="sn">03</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 4. RADIOLOGY AI AGENT -->
<section class="slide sprod">
  <div class="si">
    <div class="ey">Product 01 &middot; Radiology AI Agent</div>
    <h2 class="tt">The AWS for Radiology.</h2>
    <hr class="gr" />
    <div class="sp">
      <div>
        <div class="tg">Clinical AI.<br/><span class="g">Day&nbsp;One.</span></div>
        <div class="dc">On-premise, HIPAA-compliant. Integrates into existing PACS/HIS without replacing the radiologist. Grounded data eliminates hallucinations by reading patient notes, not just pixels.</div>
        <div class="mr">
          <div class="mb"><div class="mv"><span class="g">96.8</span>%</div><div class="ml">CT Lung sensitivity<br/><span style="font-size:10px;color:#C9A24D;">5,000 scans</span></div></div>
          <div class="mb"><div class="mv"><span class="g">94.7</span>%</div><div class="ml">Chest X-Ray sensitivity<br/><span style="font-size:10px;color:#C9A24D;">1.2M images</span></div></div>
          <div class="mb"><div class="mv"><span class="g">95.6</span>%</div><div class="ml">CT Brain sensitivity<br/><span style="font-size:10px;color:#C9A24D;">500 scans</span></div></div>
        </div>
      </div>
      <div>
        <div class="bl">
          <div class="bi"><div class="bd"></div><div class="bt"><strong>60% faster</strong> reporting TAT &mdash; radiologists process more cases per shift</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>30% fewer</strong> diagnostic errors &mdash; validated through comparative reads</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>Grounded AI</strong> &mdash; reads patient chart + imaging together, eliminating hallucinations</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>Multi-modality</strong> &mdash; CT, X-ray, MRI in one unified platform</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>Full interoperability</strong> &mdash; DICOM, HL7, PACS/RIS/HIS integration</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>FP/FN rates</strong> &mdash; CT Lung: 0.14/0.09 &middot; X-Ray: 0.18/0.12 &middot; CT Brain: 0.16/0.11</div></div>
        </div>
        <div class="hb"><div class="hv">1-in-4</div><div class="hl">strokes currently missed &mdash; our CT Brain model catches what humans miss</div></div>
      </div>
    </div>
    <div class="sn">04</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 5. WIDAS -->
<section class="slide sprod">
  <div class="si">
    <div class="ey">Product 02 &middot; WIDAS &mdash; Wound Intelligence &amp; Decision Assistance System</div>
    <h2 class="tt">Preventing amputations. &#8377;6&ndash;9 Lakhs saved per patient.</h2>
    <hr class="gr" />
    <div class="sp">
      <div>
        <div class="tg">Wound AI<br/>in under<br/><span class="g">12 seconds.</span></div>
        <div class="dc">Replaces slow culture tests (up to 5 days) and subjective visual assessments. AI classifies diabetic foot ulcers and predicts healing outcomes from a smartphone image &mdash; anywhere, instantly.</div>
        <div class="mr">
          <div class="mb"><div class="mv"><span class="g">&gt;94</span>%</div><div class="ml">Classification accuracy</div></div>
          <div class="mb"><div class="mv"><span class="g">&lt;12</span>s</div><div class="ml">Analysis time</div></div>
          <div class="mb"><div class="mv"><span class="g">93</span>%+</div><div class="ml">Doctor&ndash;AI agreement</div></div>
        </div>
      </div>
      <div>
        <div class="bl">
          <div class="bi"><div class="bd"></div><div class="bt"><strong>12,000+ wounds</strong> analyzed from official medical unit datasets</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>35&ndash;45% faster</strong> clinical workflows for wound care teams</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>Rural &amp; Tier 2/3 access</strong> &mdash; empowers non-specialists with expert-level decision support</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>Continuous monitoring</strong> &mdash; tracks healing progression over time</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>101 million</strong> Indians with diabetes today (IDF 2025) &mdash; projected 177M by 2050</div></div>
        </div>
        <div class="hb"><div class="hv">&#8377;6&ndash;9 Lakhs</div><div class="hl">saved per patient &mdash; avoided amputation costs &middot; medical economic moat in an unprioritized segment</div></div>
      </div>
    </div>
    <div class="sn">05</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 6. CBCT STRUCT -->
<section class="slide sprod">
  <div class="si">
    <div class="ey">Product 03 &middot; CBCT STRUCT &mdash; Dental Radiology AI</div>
    <h2 class="tt">Three-sector architecture. Zero copy-paste.</h2>
    <hr class="gr" />
    <div class="sp">
      <div>
        <div class="tg">From scan<br/>to report.<br/><span class="g">Instantly.</span></div>
        <div class="dc">Reorganizes the dental imaging workflow into a Three-Sector Architecture that automates every stage from analog intake to one-click delivery.</div>
        <div class="mr">
          <div class="mb"><div class="mv"><span class="g">5</span>&times;</div><div class="ml">Faster diagnostic prep</div></div>
          <div class="mb"><div class="mv"><span class="g">100</span>%</div><div class="ml">Automated intake</div></div>
          <div class="mb"><div class="mv"><span class="g">0</span></div><div class="ml">Manual copy-paste steps</div></div>
        </div>
      </div>
      <div>
        <div class="bl">
          <div class="bi"><div class="bd"></div><div class="bt"><strong>Sector 1 &mdash; Pre-Analysis:</strong> Instant LLM extraction from analog forms, auto-populates report templates</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>Sector 2 &mdash; Clinical Core:</strong> AI nerve tracing, 1mm cross-sectioning, implant measurements (e.g. 14mm nerve clearance, 5.6mm width)</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>Sector 3 &mdash; Delivery:</strong> One-Click Progression replaces manual Word doc assembly with automated UI generation</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>100K+ dental clinics</strong> in India &mdash; addressable install base</div></div>
          <div class="bi"><div class="bd"></div><div class="bt"><strong>No radiology IT team</strong> required &mdash; designed for independent dental centers</div></div>
        </div>
        <div class="hb"><div class="hv">The Heavy Lifting</div><div class="hl">AI does the technical prep before the human expert enters the loop &mdash; high adoption, minimal friction</div></div>
      </div>
    </div>
    <div class="sn">06</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 7. CLINICAL VALIDATION -->
<section class="slide s7">
  <div class="si">
    <div class="ey">Clinical Evidence</div>
    <h2 class="tt">Research-grade. Internationally validated.</h2>
    <hr class="gr" />
    <table class="vt">
      <thead><tr><th>Product</th><th>Metric</th><th>Value</th><th>Training Scale</th><th>Fleiss &kappa;</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td class="pc">Radiology AI</td><td>CT Lung sensitivity</td><td class="mv">96.8%</td><td>5,000 scans</td><td>&gt;0.82</td><td><span class="chip">Pilot Active</span></td></tr>
        <tr><td class="pc">Radiology AI</td><td>Chest X-Ray sensitivity</td><td class="mv">94.7%</td><td>1.2M images</td><td>&gt;0.82</td><td><span class="chip">Pilot Active</span></td></tr>
        <tr><td class="pc">Radiology AI</td><td>CT Brain sensitivity</td><td class="mv">95.6%</td><td>500 scans</td><td>&gt;0.82</td><td><span class="chip">Pilot Active</span></td></tr>
        <tr><td class="pc">WIDAS</td><td>Wound classification accuracy</td><td class="mv">&gt;94%</td><td>12,000+ wounds</td><td>93%+ agree</td><td><span class="chip">Pilot Active</span></td></tr>
        <tr><td class="pc">CBCT STRUCT</td><td>Diagnostic prep reduction</td><td class="mv">5&times;</td><td>Multi-center</td><td>&mdash;</td><td><span class="chip">Pilot Active</span></td></tr>
      </tbody>
    </table>
    <div class="note">
      <div class="ni"><strong>Nature &amp; Frontiers Health</strong><br/>Findings validated at top global conferences</div>
      <div class="ni"><strong>3-member radiologist consensus</strong><br/>Inter-reader Fleiss Kappa &gt; 0.82</div>
      <div class="ni"><strong>ISO 13485:2016 &middot; ISO/IEC 27001:2013</strong><br/>HIPAA-compliant &middot; On-premise data sovereignty</div>
      <div class="ni"><strong>DPIIT Certified</strong><br/>Recognized for healthcare innovation</div>
    </div>
    <div class="sn">07</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 8. MARKET OPPORTUNITY -->
<section class="slide s8">
  <div class="si">
    <div class="ey">Market Opportunity</div>
    <h2 class="tt">India: the world&rsquo;s most structurally underserved diagnostics market.</h2>
    <hr class="gr" />
    <div class="mg">
      <div>
        <div class="bs">$1.7B</div>
        <div class="bl">India Healthcare AI Market by 2027</div>
        <div class="bss">40%+ CAGR &mdash; fastest-growing AI vertical globally</div>
        <div style="margin-top:28px;">
          <div class="bs" style="font-size:56px;">101M</div>
          <div class="bl">Indians with diabetes today</div>
          <div class="bss">Projected 177 million by 2050 (IDF 2025)</div>
        </div>
        <div style="margin-top:22px;">
          <div class="bs" style="font-size:56px;">300M+</div>
          <div class="bl">Medical scans per year in India</div>
          <div class="bss">Less than 5% currently read with AI assistance</div>
        </div>
      </div>
      <div class="mi">
        <div class="mc"><div class="mv"><span class="g">5K</span>+</div><div class="md">Hospitals and diagnostic centers &mdash; primary targets for the Radiology AI Agent platform</div></div>
        <div class="mc"><div class="mv"><span class="g">100K</span>+</div><div class="md">Dental clinics performing CBCT scans &mdash; CBCT STRUCT addressable install base</div></div>
        <div class="mc"><div class="mv"><span class="g">7M</span>+</div><div class="md">Indians with active diabetic foot ulcer risk &mdash; WIDAS primary addressable market</div></div>
        <div class="mc"><div class="mv" style="font-size:16px;line-height:1.3;">SE<br/>Asia</div><div class="md">Next expansion: Indonesia, Vietnam, Bangladesh &mdash; identical radiologist shortages and data sovereignty laws</div></div>
      </div>
    </div>
    <div class="sn">08</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 9. TRACTION -->
<section class="slide s9">
  <div class="si">
    <div class="ey">Traction &middot; Q2 2026</div>
    <h2 class="tt">6&ndash;8 week Pilot-to-Enterprise Framework. Active now.</h2>
    <hr class="gr" />
    <div class="tg">
      <div class="tc">
        <div class="tp">Radiology AI Agent</div>
        <div class="tv"><span class="g">3</span>+</div>
        <div class="tl">Active hospital pilots</div>
        <div class="td">Deployed in diagnostic centers across India. Radiologists using the platform daily. Flywheel effect: AI personalizes to each hospital&rsquo;s patient demographic with every read.</div>
      </div>
      <div class="tc">
        <div class="tp">WIDAS</div>
        <div class="tv"><span class="g">12K</span>+</div>
        <div class="tl">Wounds analyzed</div>
        <div class="td">Real-world dataset from official medical unit partnerships. Model continuously improves. 35&ndash;45% faster clinical workflows confirmed by pilot clinicians.</div>
      </div>
      <div class="tc">
        <div class="tp">CBCT STRUCT</div>
        <div class="tv"><span class="g">2</span>+</div>
        <div class="tl">Dental center pilots</div>
        <div class="td">Active integrations with dental diagnostic centers. Radiologists confirming significant time savings on implant planning and impaction assessment cases.</div>
      </div>
      <div class="tc">
        <div class="tp">Pipeline</div>
        <div class="tv"><span class="g">&#8377;</span></div>
        <div class="tl">Converting to paid</div>
        <div class="td">Seed funding converts active pilots to enterprise contracts. 8-week onboarding roadmap already proven with existing pilot partners.</div>
      </div>
    </div>
    <div class="steps">
      <div class="st"><div class="sw">Weeks 1&ndash;2</div><div class="sd">PACS integration &amp; baseline setup</div></div>
      <div class="st"><div class="sw">Weeks 3&ndash;4</div><div class="sd">AI findings engine live (Chest + Brain)</div></div>
      <div class="st"><div class="sw">Weeks 5&ndash;6</div><div class="sd">Radiologist feedback loop &amp; dashboards</div></div>
      <div class="st"><div class="sw">Weeks 7&ndash;8</div><div class="sd">Review &amp; enterprise scale-up planning</div></div>
    </div>
    <div class="sn">09</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 10. BUSINESS MODEL -->
<section class="slide s10">
  <div class="si">
    <div class="ey">Business Model</div>
    <h2 class="tt">Transparent unit economics. ROI from Day 1.</h2>
    <hr class="gr" />
    <div class="bg">
      <div class="bc">
        <div class="bt2">Platform Fees</div>
        <div class="bh">Setup + Monthly SaaS</div>
        <table>
          <thead><tr><th>Hospital Size</th><th>One-Time Setup</th><th>Monthly Fee</th></tr></thead>
          <tbody>
            <tr><td>50 Beds</td><td class="mv">&#8377;4,00,000</td><td class="mv">&#8377;50,000</td></tr>
            <tr><td>100 Beds</td><td class="mv">&#8377;6,00,000</td><td class="mv">&#8377;1,00,000</td></tr>
            <tr><td>250 Beds</td><td class="mv">&#8377;12,00,000</td><td class="mv">&#8377;2,50,000</td></tr>
            <tr><td>500+ Beds</td><td class="mv">&#8377;24,00,000</td><td class="mv">&#8377;6,00,000</td></tr>
          </tbody>
        </table>
      </div>
      <div class="bc">
        <div class="bt2">Annual Projections (&#8377;22.5/scan avg)</div>
        <div class="bh">Per-Scan Revenue</div>
        <table>
          <thead><tr><th>Bed Size</th><th>Annual Scans</th><th>Annual Revenue</th></tr></thead>
          <tbody>
            <tr><td>50 Beds</td><td>~7,300</td><td class="mv">&#8377;1.64L</td></tr>
            <tr><td>100 Beds</td><td>~14,600</td><td class="mv">&#8377;3.28L</td></tr>
            <tr><td>500+ Beds</td><td>73,000+</td><td class="mv">&#8377;16.4L+</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <div class="bb">
      <div class="bbt">&#8377;10&ndash;&#8377;35 per scan &mdash; <span>accelerated TAT + reduced medico-legal risk from Day 1</span></div>
      <div class="bbn">Enterprise API + tele-radiology network contracts available &middot; White-label licensing for diagnostic groups</div>
    </div>
    <div class="sn">10</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 11. TEAM -->
<section class="slide s11">
  <div class="si">
    <div class="ey">Leadership</div>
    <h2 class="tt">Research pedigree. Clinical reality. Hospital-ready.</h2>
    <hr class="gr" />
    <div class="tg">
      <div class="tc">
        <div class="av">SK</div>
        <div class="tn">Sonu Kumar</div>
        <div class="tr">Founder &amp; CEO</div>
        <div class="tb">Product strategy, clinical partnerships, GTM. Built and deployed all three AI products into active pilots. Expert in regulated-market healthcare AI.</div>
      </div>
      <div class="tc">
        <div class="av">AI</div>
        <div class="tn">AI / ML Lead</div>
        <div class="tr">Head of AI</div>
        <div class="tb">Model development, clinical validation, continuous learning pipelines. Published in Nature and Frontiers Health. Agentic AI architecture specialist.</div>
      </div>
      <div class="tc">
        <div class="av">CL</div>
        <div class="tn">Clinical Director</div>
        <div class="tr">Medical Advisor</div>
        <div class="tb">Senior radiologist. Leads clinical accuracy standards, 3-member consensus reads, and regulatory strategy for CDSCO, CE Mark, and FDA pathways.</div>
      </div>
      <div class="tc">
        <div class="av">BD</div>
        <div class="tn">Partnerships Lead</div>
        <div class="tr">Head of BD</div>
        <div class="tb">Manages hospital pipeline and enterprise contracts. Proven 6&ndash;8 week pilot-to-enterprise conversion framework across all three products.</div>
      </div>
    </div>
    <div class="cert">
      <div class="cert-text">
        <strong>DPIIT Certified Startup</strong> &middot; <strong>ISO 13485:2016</strong> Medical Device QMS &middot; <strong>ISO/IEC 27001:2013</strong> Information Security &middot; <strong>HIPAA Compliant</strong> &middot; On-premise data sovereignty &middot; No external cloud API
      </div>
    </div>
    <div class="sn">11</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

<!-- 12. THE ASK -->
<section class="slide s12">
  <div class="si">
    <div class="ey">Seed Round &middot; 2026</div>
    <h2 class="tt">Partner with us to save lives at scale.</h2>
    <hr class="gr" />
    <div class="ab">
      <div>
        <div class="aa">$<span class="g">3M</span></div>
        <div class="al">Seed Round &mdash; converting pilots to enterprise revenue</div>
        <div class="au">
          <div class="ui"><div class="up">35%</div><div class="ud">GTM scaling &mdash; accelerating deployment across national hospital networks</div></div>
          <div class="ui"><div class="up">25%</div><div class="ud">Modality expansion &mdash; broadening clinical reach of AI Agent and WIDAS</div></div>
          <div class="ui"><div class="up">25%</div><div class="ud">Deep integration &mdash; PACS/HIS vendors (Philips, Fuji, GE)</div></div>
          <div class="ui"><div class="up">15%</div><div class="ud">Regulatory approvals &mdash; CDSCO, CE Mark, FDA pathway</div></div>
        </div>
      </div>
      <div>
        <div class="cb">
          <div class="ct">Let&rsquo;s build India&rsquo;s healthcare AI infrastructure.</div>
          <div class="ci"><div class="ck">Founder</div><div class="cv">Sonu Kumar</div></div>
          <div class="ci"><div class="ck">Email</div><div class="cv"><a href="mailto:sonu@aianytime.net">sonu@aianytime.net</a></div></div>
          <div class="ci"><div class="ck">Web</div><div class="cv"><a href="https://kodryx-presentation.vercel.app" target="_blank">kodryx-presentation.vercel.app</a></div></div>
          <div class="ci"><div class="ck">Stage</div><div class="cv">Seed &mdash; active pilots across 3 products, raising $3M</div></div>
          <div class="ci"><div class="ck">Certified</div><div class="cv">DPIIT &middot; ISO 13485 &middot; HIPAA compliant</div></div>
          <a class="cta" href="mailto:sonu@aianytime.net?subject=Kodryx AI - Seed Round Interest">Request Full Data Room &rarr;</a>
        </div>
      </div>
    </div>
    <div class="sn">12</div>
    <div class="fl">{LOGO}</div>
  </div>
</section>

</div></div>

<div id="nav">
  <button id="bp" disabled>&#8592;</button>
  <div id="dots"></div>
  <span id="ctr">1 / 12</span>
  <button id="bn">&#8594;</button>
</div>

<script>
(function(){{
  const slides=document.querySelectorAll('.slide'),total=slides.length;
  let cur=0;
  const dotsEl=document.getElementById('dots'),ctr=document.getElementById('ctr'),bp=document.getElementById('bp'),bn=document.getElementById('bn');
  slides.forEach((_,i)=>{{const d=document.createElement('div');d.className='dot'+(i===0?' on':'');d.onclick=()=>go(i);dotsEl.appendChild(d);}});
  function go(n){{slides[cur].classList.remove('on');dotsEl.children[cur].classList.remove('on');cur=Math.max(0,Math.min(n,total-1));slides[cur].classList.add('on');dotsEl.children[cur].classList.add('on');ctr.textContent=(cur+1)+' / '+total;bp.disabled=cur===0;bn.disabled=cur===total-1;}}
  bp.onclick=()=>go(cur-1);bn.onclick=()=>go(cur+1);
  function scale(){{const s=Math.min(window.innerWidth/1440,window.innerHeight/810);document.getElementById('stage').style.transform='scale('+s+')';}}
  window.onresize=scale;scale();
  document.onkeydown=e=>{{if(e.key==='ArrowRight'||e.key===' ')go(cur+1);if(e.key==='ArrowLeft')go(cur-1);if(e.key==='Home')go(0);if(e.key==='End')go(total-1);}};
}})();
</script>
</body>
</html>"""

output = "C:/Vibe Code/Investment/APEX-ASCENSION-HEALTHCARE-PITCH.html"
with open(output, "w", encoding="utf-8") as f:
    f.write(html)
print(f"OK: {len(html):,} chars -> {output}")
