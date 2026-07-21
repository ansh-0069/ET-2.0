import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT = "D:/Coding/PROJECTS/ET 2.0/outputs";
const TMP = "D:/Coding/PROJECTS/ET 2.0/outputs/petravigil-grand-final-tmp";
const W = 1280, H = 720;
const C = {
  bg: "#07111F", panel: "#0D1D31", panel2: "#102741", line: "#244563",
  white: "#F5F8FC", mute: "#AABFD2", blue: "#66B3FF", cyan: "#51E5D6",
  amber: "#FFC56E", red: "#F58D95", green: "#86E5B6", ink: "#07111F",
};

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

function add(slide, text, x, y, w, h, size = 22, color = C.white, bold = false, name = "text") {
  const s = slide.shapes.add({ geometry: "textbox", name, position: { left: x, top: y, width: w, height: h }, fill: "none", line: { style: "solid", fill: "none", width: 0 } });
  s.text = text;
  s.text.style = { fontSize: size, color, bold, fontFace: "Aptos" };
  return s;
}
function box(slide, x, y, w, h, fill = C.panel, line = C.line, radius = "rounded-xl", name = "panel") {
  return slide.shapes.add({ geometry: "roundRect", name, position: { left: x, top: y, width: w, height: h }, fill, line: { style: "solid", fill: line, width: 1 }, borderRadius: radius });
}
function ellipse(slide, x, y, w, h, fill, line = fill, name = "ellipse") {
  return slide.shapes.add({ geometry: "ellipse", name, position: { left: x, top: y, width: w, height: h }, fill, line: { style: "solid", fill: line, width: 1 } });
}
function rule(slide, x, y, w, color = C.line, width = 1) {
  return slide.shapes.add({ geometry: "line", position: { left: x, top: y, width: w, height: 0 }, fill: "none", line: { style: "solid", fill: color, width } });
}
function chip(slide, text, x, y, w, color = C.blue) {
  const b = box(slide, x, y, w, 30, "#102B47", color, "rounded-full", "chip");
  b.text = text;
  b.text.style = { fontSize: 12, color, bold: true, fontFace: "Aptos" };
  return b;
}
function eyebrow(slide, text, n) { add(slide, text.toUpperCase(), 72, 50, 700, 22, 13, C.cyan, true, "eyebrow"); add(slide, `0${n}`, 1150, 50, 58, 22, 13, C.mute, true, "slide-number"); }
function title(slide, text, sub = "") { add(slide, text, 72, 90, 1050, 100, 42, C.white, true, "title"); if (sub) add(slide, sub, 72, 196, 1000, 50, 20, C.mute, false, "subtitle"); }
function footer(slide, text = "PETRAVIGIL · GRAND FINAL") { rule(slide, 72, 670, 1136, C.line, 1); add(slide, text, 72, 681, 500, 18, 11, C.mute, true, "footer"); }
function note(slide, body) { slide.speakerNotes.textFrame.setText(body); slide.speakerNotes.setVisible(true); }
function metric(slide, value, label, x, y, w, tone = C.blue) { box(slide, x, y, w, 118, C.panel, C.line, "rounded-xl", "metric"); add(slide, value, x + 18, y + 18, w - 36, 48, 32, tone, true, "metric-value"); add(slide, label, x + 18, y + 76, w - 36, 30, 15, C.mute, false, "metric-label"); }
function node(slide, label, x, y, w, tone = C.blue) { box(slide, x, y, w, 66, C.panel, tone, "rounded-xl", "node"); add(slide, label, x + 13, y + 18, w - 26, 32, 16, C.white, true, "node-label"); }

const p = Presentation.create({ slideSize: { width: W, height: H } });

// 1. Hook
{
  const s = p.slides.add(); s.background.fill = C.bg;
  add(s, "PETRAVIGIL", 72, 64, 310, 26, 16, C.cyan, true, "brand");
  add(s, "When a chokepoint moves,\nIndia needs a decision—\nnot another dashboard.", 72, 148, 720, 230, 54, C.white, true, "hero-title");
  add(s, "Evidence-first energy supply resilience", 76, 410, 520, 30, 22, C.mute, false, "tagline");
  chip(s, "ANALYST-CONFIRMED", 76, 470, 182, C.cyan);
  // Striking visual: signal chain becomes an evidence-backed decision.
  ellipse(s, 850, 143, 250, 250, "#0E3154", "#2A78B7", "hero-orbit");
  ellipse(s, 900, 193, 150, 150, "#123E66", "#51E5D6", "hero-core");
  add(s, "DECISION", 918, 245, 118, 28, 18, C.white, true, "decision");
  add(s, "not a prediction\n— a reviewable action", 886, 292, 182, 52, 14, C.mute, false, "decision-sub");
  const steps = [["SIGNAL", 750, 455, C.red], ["RISK", 894, 455, C.amber], ["ACTION", 1038, 455, C.green]];
  for (const [label, x, y, tone] of steps) { ellipse(s, x, y, 90, 90, C.panel, tone, "hero-step"); add(s, label, x + 12, y + 36, 66, 20, 12, tone, true, "hero-step-label"); }
  rule(s, 795, 500, 95, C.line, 2); rule(s, 939, 500, 95, C.line, 2);
  add(s, "The product that helps India decide before the market does.", 76, 562, 690, 32, 22, C.blue, true, "memorable-line");
  footer(s);
  note(s, "India's energy supply chain does not fail because leaders lack dashboards. It fails when a moving disruption turns into a late, opaque decision. PetraVigil is built for that exact moment: it turns one source-labelled signal into a reviewable procurement decision, with the analyst still in control. This is not an AI that buys crude. It is decision intelligence that shows its work.\n\nTransition: Why does this matter enough to act now? Because India’s exposure is structural, not theoretical.");
}

// 2. Problem
{
  const s = p.slides.add(); s.background.fill = C.bg; eyebrow(s, "Act 1 · The problem", 2); title(s, "India cannot wait for a crisis call.", "When disruption hits, the cost of delay compounds across energy, freight, and refining.");
  metric(s, "88%", "of India’s crude needs are met through imports", 72, 295, 320, C.cyan);
  add(s, "The signal-to-decision gap", 460, 290, 400, 26, 18, C.mute, true, "gap-label");
  const flow = [["Fragmented signal", "news · shipping · insurance", C.red], ["Manual interpretation", "spreadsheets · calls", C.amber], ["Late decision", "panic-market timing", C.red]];
  for (let i = 0; i < flow.length; i++) { const [a,b,t] = flow[i]; const x = 460 + i * 230; box(s,x,335,200,142,C.panel,C.line,"rounded-xl","problem-step"); add(s,a,x+16,358,168,44,19,C.white,true,"problem-head"); add(s,b,x+16,415,168,38,14,C.mute,false,"problem-copy"); ellipse(s,x+16,480,10,10,t,t,"problem-dot"); if(i<2) rule(s,x+200,406,30,C.line,2); }
  add(s, "No single place connects a signal, its assumptions, an impact range, and a constrained alternative.", 72, 520, 1050, 36, 25, C.white, true, "problem-statement");
  add(s, "Source: Government of India, Press Information Bureau (2025): India meets about 88% of crude needs through imports.", 72, 608, 970, 24, 12, C.mute, false, "source"); footer(s);
  note(s, "The urgency is simple: India meets about 88 percent of its crude needs through imports. A disruption is not just a news event; it becomes a procurement, route, refinery, and cost decision. Today those threads are often separated—signals in one place, alternatives in another, approvals elsewhere. The consequence is slower, more reactive timing when the market is least forgiving.\n\nTransition: The issue is not a lack of data. It is that generic tools overlook the physics and accountability of the decision.");
}

// 3. Insight
{
  const s = p.slides.add(); s.background.fill = C.bg; eyebrow(s, "Act 2 · The insight", 3); title(s, "The blind spot: oil is not fungible.", "A route that avoids disruption is useless if the crude cannot run in the refinery—or the capacity is not there.");
  box(s, 72, 294, 472, 270, C.panel, C.line, "rounded-xl", "generic-tools"); add(s, "GENERIC RISK TOOLS", 98, 320, 260, 20, 13, C.mute, true, "generic-label");
  add(s, "Alert\n↓\n“Consider alternatives”", 98, 365, 280, 132, 27, C.white, true, "generic-flow");
  box(s, 600, 294, 608, 270, "#102B47", C.blue, "rounded-xl", "petravigil-insight"); add(s, "PETRAVIGIL’S DECISION MODEL", 628, 320, 350, 20, 13, C.cyan, true, "pv-label");
  const checks = [["1", "Corridor exposure", C.red], ["2", "Refinery-grade fit", C.amber], ["3", "Route capacity", C.blue], ["4", "Human approval", C.green]];
  for (let i=0;i<checks.length;i++) { const [n,label,t]=checks[i]; const x=628+(i%2)*270, y=365+Math.floor(i/2)*86; ellipse(s,x,y,34,34,t,t,"check-circle"); add(s,n,x+11,y+8,13,18,13,C.ink,true,"check-num"); add(s,label,x+50,y+8,190,22,17,C.white,true,"check-label"); }
  add(s, "The differentiator is not “AI writes a recommendation.”\nIt is making the recommendation feasible, explainable, and accountable.", 72, 600, 1010, 50, 23, C.white, true, "insight-conclusion"); footer(s);
  note(s, "Most risk products stop at an alert, and most generic supply tools treat oil as interchangeable. But a decision is only useful if it respects the refinery’s compatible crude grades, alternative-route capacity, corridor exposure, and a named human approver. PetraVigil makes those constraints part of the product—not a spreadsheet after the fact.\n\nTransition: That insight leads to a very different kind of workflow.");
}

// 4. Solution
{
  const s = p.slides.add(); s.background.fill = C.bg; eyebrow(s, "Act 3 · The solution", 4); title(s, "One signal. One reviewable decision.", "PetraVigil links every stage—from intake to human decision—into a single case record.");
  const labels = [["01", "Signal", C.red], ["02", "Extract & resolve", C.blue], ["03", "Score risk", C.amber], ["04", "Confirm assumptions", C.cyan], ["05", "Simulate & optimize", C.blue], ["06", "Decide", C.green]];
  for (let i=0;i<labels.length;i++) { const [n,l,t]=labels[i]; const x=72+i*187; if (i<5) rule(s,x+156,402,31,C.line,2); node(s,`${n}  ${l}`,x,370,156,t); }
  box(s, 266, 490, 748, 76, "#102B47", C.cyan, "rounded-xl", "human-gate"); add(s, "THE CONTROL POINT  ·  Analyst confirms visible assumptions before simulation and procurement comparison run.", 294, 515, 695, 30, 17, C.white, true, "gate-text");
  chip(s,"USER-ENTERED SIGNAL",72,603,180,C.amber); chip(s,"SIMULATED SCENARIO",270,603,180,C.blue); chip(s,"LOCAL-ONLY DECISION",468,603,180,C.green); footer(s);
  note(s, "Here is the product in one line: a source-labelled signal becomes a case, the system extracts and resolves what it can, scores corridor risk, and then stops. The analyst sees and confirms the assumptions. Only then do the simulation and portfolio comparison run. The outcome is recorded locally—never sent as a purchase order or supplier instruction.\n\nTransition: That workflow is deliberately structured so AI has a precise job, not unchecked authority.");
}

// 5. AI
{
  const s = p.slides.add(); s.background.fill = C.bg; eyebrow(s, "AI advantage", 5); title(s, "AI earns its place only when it is constrained.", "Gemini interprets and explains; deterministic models calculate and choose within explicit limits.");
  const cols = [["Gemini", "STRUCTURES\nA SIGNAL", "Schema-validated proposal\nConfidence and uncertainty disclosed", C.cyan], ["Risk + scenario", "QUANTIFIES\nEXPOSURE", "Deterministic corridor score\nReproducible Monte Carlo ranges", C.amber], ["Optimizer", "FINDS\nFEASIBLE OPTIONS", "OR-Tools allocation with\ncompatibility and capacity constraints", C.blue]];
  for (let i=0;i<cols.length;i++) { const [head,verb,body,t] = cols[i]; const x=72+i*380; box(s,x,300,344,248,C.panel,C.line,"rounded-xl","ai-column"); add(s,head,x+24,328,180,22,17,t,true,"ai-head"); add(s,verb,x+24,370,280,56,23,C.white,true,"ai-verb"); rule(s,x+24,446,296,C.line,1); add(s,body,x+24,466,290,55,16,C.mute,false,"ai-body"); }
  box(s,72,590,1136,54,"#1A2633",C.line,"rounded-xl","no-blackbox"); add(s,"Never delegated to AI: prices, capacity, legal status, commercial availability, or approval.",96,606,1050,24,18,C.white,true,"no-blackbox-copy"); footer(s);
  note(s, "Our AI story is intentionally sober. Gemini turns unstructured input into a structured proposal and later explains the selected portfolio. It does not create prices, approve suppliers, or invent legal status. The risk score is deterministic. The scenario engine is reproducible. The optimizer respects compatibility and capacity constraints. That separation is how we turn AI from a demo trick into decision support a procurement leader can inspect.\n\nTransition: Let me make that concrete with the canonical Hormuz case already implemented in the product.");
}

// 6. Demo narrative
{
  const s = p.slides.add(); s.background.fill = C.bg; eyebrow(s, "Demo story · canonical simulated case", 6); title(s, "A Hormuz signal becomes an action path.", "The numbers below are explicitly simulated fixture outputs—not live market claims.");
  const steps = [["Signal detected", "Shipping / insurance cues near Hormuz", C.red], ["Risk identified", "Persian Gulf → West India · 78/100", C.amber], ["Scenario run", "P50: 1.2M bpd impact · +$6.5/bbl", C.blue], ["Recommendation", "150k bpd WTI Midland via Cape route", C.cyan], ["Decision", "Human approval recorded locally", C.green]];
  for (let i=0;i<steps.length;i++) { const [h,b,t]=steps[i]; const x=72+i*227; ellipse(s,x+76,310,70,70,C.panel,t,"demo-ring"); add(s,String(i+1),x+100,334,22,25,19,t,true,"demo-number"); if(i<4) rule(s,x+147,345,80,C.line,2); add(s,h,x+2,404,215,28,17,C.white,true,"demo-head"); add(s,b,x+2,442,215,58,14,C.mute,false,"demo-body"); }
  add(s,"Every result carries its evidence, assumptions, alternatives, and unknowns forward.",72,565,1020,30,23,C.white,true,"demo-conclusion");
  chip(s,"SIMULATED",72,618,114,C.amber); chip(s,"REPRODUCIBLE",201,618,136,C.cyan); chip(s,"NO EXTERNAL EXECUTION",352,618,194,C.green); footer(s);
  note(s, "Imagine a shipping advisory reports elevated military activity near Hormuz. PetraVigil retains it as user-entered evidence, extracts a structured proposal, resolves the corridor, and surfaces a 78 out of 100 simulated corridor-risk score. The analyst confirms the scenario assumptions. In the canonical simulated case, we then see a P50 1.2 million bpd supply impact and a 6.5 dollar-per-barrel Brent premium. The system proposes a refinery-compatible 150 thousand bpd WTI Midland alternative via the Cape route—then waits for a human decision.\n\nTransition: The key is that the product does not hide the trade-off behind a single “best” answer.");
}

// 7. Decision and impact
{
  const s = p.slides.add(); s.background.fill = C.bg; eyebrow(s, "Decision intelligence", 7); title(s, "The output is a choice—not a black box.", "Decision-makers compare risk, cost, and resilience before calling anything “best.”");
  const ports = [["DO NOTHING", "Exposed", C.red], ["LOWEST COST", "Constrained allocation", C.amber], ["BALANCED", "Diversified allocation", C.cyan], ["MAX RESILIENCE", "Lower route risk", C.green]];
  for (let i=0;i<ports.length;i++) { const [h,b,t]=ports[i]; const x=72+i*283; box(s,x,310,258,142,i===2?"#123B61":C.panel,i===2?C.cyan:C.line,"rounded-xl","portfolio"); add(s,h,x+18,332,222,22,15,t,true,"portfolio-label"); add(s,b,x+18,376,222,27,20,C.white,true,"portfolio-value"); add(s,i===2?"Example of a visible trade-off":"Feasible within seeded constraints",x+18,420,222,24,13,C.mute,false,"portfolio-copy"); }
  box(s,72,500,1136,105,"#102B47",C.blue,"rounded-xl","evidence-box"); add(s,"Why this recommendation won",96,522,320,22,16,C.cyan,true,"why-label"); add(s,"Evidence chain  ·  confirmed assumptions  ·  simulation range  ·  rejected alternatives  ·  unresolved risks",96,555,1030,28,20,C.white,true,"why-copy");
  add(s,"This is how a team can challenge the decision before a crisis makes the choice for them.",72,624,1060,24,17,C.mute,false,"decision-note"); footer(s);
  note(s, "The final deliverable is not a score or a chatbot answer. It is a comparison: do nothing, optimize for lowest cost, balance the trade-off, or prioritize resilience. The selected option is accompanied by the evidence chain, analyst-confirmed assumptions, simulated impact range, rejected alternatives, and the open unknowns. That makes the recommendation contestable—which is exactly what a high-stakes decision needs.\n\nTransition: And it is built with a credible boundary between what works today and what becomes live in a pilot.");
}

// 8. Delivery / scale
{
  const s = p.slides.add(); s.background.fill = C.bg; eyebrow(s, "Why this can deploy", 8); title(s, "Built for a credible pilot—not a fictional control room.", "The MVP is complete end-to-end today; live feeds and commercial checks are clearly scoped next.");
  box(s,72,292,520,270,C.panel,C.line,"rounded-xl","now"); add(s,"WORKING NOW",98,320,250,20,14,C.green,true,"now-label");
  add(s,"• FastAPI + Next.js decision workspace\n• SQLite case and approval records\n• Pydantic-validated contracts\n• NumPy simulation + OR-Tools optimization\n• 22 backend regression tests passing",98,365,440,160,18,C.white,false,"now-list");
  box(s,656,292,552,270,"#102B47",C.blue,"rounded-xl","next"); add(s,"PILOT INTEGRATIONS",682,320,260,20,14,C.cyan,true,"next-label");
  add(s,"• Trusted AIS, news, price, and sanctions adapters\n• Commercial availability, tanker, port, and legal checks\n• Production knowledge graph and governed deployments\n• Existing architecture documents define the path",682,365,470,144,18,C.white,false,"next-list");
  rule(s,592,428,64,C.cyan,3); add(s,"PROTOTYPE → PILOT",539,582,210,24,15,C.mute,true,"arrow-label");
  add(s,"Trust comes from making the boundary visible.",72,620,760,30,23,C.white,true,"scale-conclusion"); footer(s);
  note(s, "We are not asking you to believe a fictional control room. The MVP is a working, vertically complete chain: FastAPI and Next.js, typed contracts, persistent local case records, reproducible NumPy scenarios, OR-Tools optimization, and a passing backend regression suite. The production path is also clear: connect trusted feeds and commercial validation into the same governed workflow. Importantly, those integrations are roadmap, not demo theatre.\n\nTransition: That clarity is why this project deserves to win.");
}

// 9. Closing
{
  const s = p.slides.add(); s.background.fill = C.bg; eyebrow(s, "Why we win", 9); title(s, "A practical system for the decisions that cannot wait.", "PetraVigil is designed around the real failure mode: late, unexplainable action in a moving crisis.");
  const points = [["Problem fit", "India’s import exposure meets chokepoint risk", C.red], ["Innovation", "AI + simulation + constraints + human gate", C.cyan], ["Engineering", "Linked workflow, reproducible runs, tested safeguards", C.blue], ["Readiness", "Clear prototype limits and pilot path", C.green]];
  for (let i=0;i<points.length;i++) { const [h,b,t]=points[i]; const x=72+(i%2)*568, y=294+Math.floor(i/2)*118; box(s,x,y,540,92,C.panel,C.line,"rounded-xl","win-point"); ellipse(s,x+22,y+24,44,44,t,t,"win-dot"); add(s,String(i+1),x+38,y+37,14,16,15,C.ink,true,"win-num"); add(s,h,x+88,y+22,190,22,18,t,true,"win-head"); add(s,b,x+88,y+50,420,22,15,C.white,false,"win-copy"); }
  add(s,"The winning product doesn’t decide for India.\nIt helps India decide before the market does.",72,570,1020,76,34,C.white,true,"closing-line");
  chip(s,"EVIDENCE-FIRST",72,650,144,C.cyan); chip(s,"HUMAN-CONTROLLED",232,650,172,C.green); footer(s,"PETRAVIGIL · DECISION INTELLIGENCE FOR ENERGY RESILIENCE");
  note(s, "Why should this win? Because it is practical. We understood the problem as an evidence-to-action gap, not a dashboard gap. We use AI where language and explanation help, deterministic models where math matters, and humans where accountability belongs. We built the complete workflow, tested the safeguards, and drew a clean line between a working prototype and a future pilot. PetraVigil does not decide for India. It helps India decide before the market does.\n\nTransition: Thank you. We welcome questions on the workflow, the model assumptions, and the pilot path.");
}

await fs.mkdir(TMP, { recursive: true });
for (const [i, slide] of p.slides.items.entries()) {
  const png = await p.export({ slide, format: "png", scale: 1 });
  await writeBlob(`${TMP}/slide-${String(i + 1).padStart(2, "0")}.png`, png);
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${TMP}/slide-${String(i + 1).padStart(2, "0")}.layout.json`, await layout.text());
}
const montage = await p.export({ format: "webp", montage: true, scale: 1 });
await writeBlob(`${TMP}/deck-montage.webp`, montage);
const pptx = await PresentationFile.exportPptx(p);
await pptx.save(`${OUT}/PetraVigil-Grand-Final-Pitch-Deck.pptx`);
