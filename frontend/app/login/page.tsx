"use client";
import { FormEvent, useState } from "react";
import { login } from "../../lib/auth";

export default function LoginPage() {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(""); try { await login(email, password); window.location.href = "/"; } catch (e) { setError(e instanceof Error ? e.message : "Unable to sign in"); } finally { setBusy(false); } }
  return <main style={{ maxWidth: 440, margin: "80px auto", padding: 32 }}><h1>Sign in to NicheForge</h1><p>Use your NicheForge account to continue.</p><form onSubmit={submit} style={{ display: "grid", gap: 16 }}><label>Email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} /></label><label>Password<input required type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>{error && <p role="alert">{error}</p>}<button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button></form></main>;
}
