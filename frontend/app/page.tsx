import Link from "next/link";
import { AppShell } from "./components/AppShell";

export default function Overview() {
  return <AppShell active="Overview">
    <div className="page-head"><div><p className="eyebrow">Workspace overview</p><h1>Overview</h1><p className="muted">Track search-demand research, validation progress, and evidence activity.</p></div><div className="head-actions"><Link className="button primary" href="/research/search-volume">New Search Volume Research</Link><Link className="button secondary" href="/rank-rent/validator">New Validation Run</Link></div></div>
    <div className="metric-grid"><Metric title="Keywords Researched"/><Metric title="Cities Researched"/><Metric title="Valid Evidence"/><Metric title="Rank & Rent Eligible"/></div>
    <div className="dashboard-grid"><section className="card"><div className="section-head"><div><h2>Recent Research</h2><p className="muted">Your latest search-volume activity will appear here.</p></div><Link className="text-link" href="/research/search-volume">Start research →</Link></div><Empty title="No search-volume research yet" body="Run a keyword across one or more locations to begin building evidence." href="/research/search-volume" label="Start Search Volume Research"/></section><section className="card"><div className="section-head"><div><h2>Rank & Rent Validation</h2><p className="muted">Move qualified evidence through your validation workflow.</p></div></div><div className="pipeline"><span>Candidates</span><i>→</i><span>Population</span><i>→</i><span>Search Volume</span><i>→</i><span>SERP / DA</span><i>→</i><span>Result</span></div><Empty title="No active validation run" body="Create a run when your research set is ready." href="/rank-rent/validator" label="Create Validation Run"/></section></div>
    <section className="card provider-card"><div><h2>Data Sources</h2><p className="muted">Connection status is shown without exposing credentials.</p></div><div className="provider-list"><Status name="Google Ads"/><Status name="FX normalization"/><Status name="Authority providers"/></div></section>
  </AppShell>
}
function Metric({title}:{title:string}) { return <div className="metric card"><span className="muted">{title}</span><strong>—</strong><small>No research yet</small></div> }
function Status({name}:{name:string}) { return <div className="provider"><span>{name}</span><span className="badge neutral">Not checked</span></div> }
function Empty({title,body,href,label}:{title:string;body:string;href:string;label:string}) { return <div className="empty"><div className="empty-mark">+</div><h3>{title}</h3><p className="muted">{body}</p><Link className="button secondary" href={href}>{label}</Link></div> }
