import type { ReactNode } from "react";

import "./auth-card.css";

interface AuthCardProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

/**
 * Glass card for auth forms (login/signup) over the persistent globe. Its title is the screen's
 * main heading (`h1`): the public header carries only the logo link, no other headings.
 */
export function AuthCard({ title, subtitle, children }: AuthCardProps) {
  return (
    <section className="auth-card">
      <h1 className="auth-card__title">{title}</h1>
      <p className="auth-card__subtitle">{subtitle}</p>
      {children}
    </section>
  );
}
