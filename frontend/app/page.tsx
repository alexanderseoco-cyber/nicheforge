"use client";
import React, {useState} from "react";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

type Candidate = {id:string;keyword:string;city?:string;state?:string;population?:number;search_volume?:number;cpc?:number;low_da_count?:number;status:string;automatic_pass?:boolean;reason_codes:string[]};

export default function Page(){
  const [projectId,setProjectId]=useState("");
  const [rows,setRows]=useState<Candidate[]>([]);
  const [name,setName]=useState("Pest Control Research");
  const [sv,setSv]=useState(300); const [da,setDa]=useState(10); const [need,setNeed]=useState(5);
  async function create(){
    const r=await fetch(`${API}/projects`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,profile:{min_population:20000,max_population:120000,min_search_volume:sv,da_threshold:da,required_low_da_count:need,organic_depth:10}})});
    const j=await r.json(); setProjectId(j.id);
  }
  async function load(){ if(!projectId)return; const r=await fetch(`${API}/projects/${projectId}/candidates`); setRows(await r.json()); }
  return <main style={{maxWidth:1400,margin:"0 auto",padding:24}}>
    <h1>NicheForge</h1><p>Rank & Rent Niche Intelligence Engine</p>
    <section style={{display:"flex",gap:12,flexWrap:"wrap",background:"white",padding:16,borderRadius:12}}>
      <input value={name} onChange={e=>setName(e.target.value)} />
      <label>Min SV <input type="number" value={sv} onChange={e=>setSv(+e.target.value)} style={{width:80}}/></label>
      <label>DA &lt; <input type="number" value={da} onChange={e=>setDa(+e.target.value)} style={{width:60}}/></label>
      <label>Weak sites required <input type="number" value={need} onChange={e=>setNeed(+e.target.value)} style={{width:60}}/></label>
      <button onClick={create}>Create project</button><button onClick={load}>Refresh candidates</button>
    </section>
    <p>Project: {projectId || "not created"}</p>
    <div style={{overflowX:"auto",background:"white",borderRadius:12}}><table style={{borderCollapse:"collapse",width:"100%"}}>
      <thead><tr>{["Keyword","City","Pop","SV","CPC","DA< threshold","Status","Reasons"].map(x=><th key={x} style={{textAlign:"left",padding:8,borderBottom:"1px solid #ddd"}}>{x}</th>)}</tr></thead>
      <tbody>{rows.map(r=><tr key={r.id}><td>{r.keyword}</td><td>{r.city} {r.state}</td><td>{r.population}</td><td>{r.search_volume}</td><td>{r.cpc}</td><td>{r.low_da_count}</td><td>{r.status}</td><td>{r.reason_codes?.join(", ")}</td></tr>)}</tbody>
    </table></div>
  </main>;
}
