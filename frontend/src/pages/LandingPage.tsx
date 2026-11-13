import { Trans, useTranslation } from "react-i18next";
import { Link } from "react-router";

import "./landing.css";

/** Copy item of the features section (from i18n `landing:features.items`). */
interface FeatureItem {
  stamp: string;
  title: string;
  body: string;
}

/** Itinerary step (from i18n `landing:steps.items`). */
interface StepItem {
  no: string;
  title: string;
  body: string;
  stamp: string;
}

/** Stat cell of the sample atlas (from i18n `landing:atlas.stats`). */
interface AtlasStat {
  value: string;
  label: string;
}

const BRAND = "MyJourney";

/**
 * Array of objects from i18n, or an empty array.
 *
 * `t(key, { returnObjects: true })` is typed as `string`, and a cast stays silent when the key is
 * missing: i18next returns the key string itself, `.map` on a string throws, and the landing (the
 * only page for anonymous users) goes blank over a JSON typo. Check the shape at the boundary.
 */
function itemsFromTranslation<T>(value: unknown): readonly T[] {
  return Array.isArray(value) ? (value as readonly T[]) : [];
}

/**
 * Public MyJourney landing. The hero is transparent: the persistent globe from `PublicLayout`
 * shows through it; below, the content (features -> how it works -> sample atlas) sits on an
 * opaque night that covers the planet and ends with a CTA footer.
 *
 * The page rhythm comes from surface ELEVATION, not brightness inversion: the "how it works"
 * band is raised, cards have a hairline outline, the journal clipping is sunk deeper than the
 * background.
 *
 * All copy comes from the i18n namespace `landing` (EN/RU). There is no globe of its own: the
 * background comes from the layout, so one WebGL instance survives the move into the auth zone.
 */
export function LandingPage() {
  const { t } = useTranslation("landing");

  const features = itemsFromTranslation<FeatureItem>(t("features.items", { returnObjects: true }));
  const steps = itemsFromTranslation<StepItem>(t("steps.items", { returnObjects: true }));
  const stats = itemsFromTranslation<AtlasStat>(t("atlas.stats", { returnObjects: true }));

  return (
    <div className="lp">
      {/* The header is shared by the public zone and lives in `PublicLayout` (survives navigation). */}

      {/* --- Hero (transparent: the fixed globe is behind it) --- */}
      <section className="lp-hero">
        <div className="lp-hero__scrim" />

        <div className="lp-hero__inner">
          <div className="lp-hero__copy">
            <p className="lp-eyebrow">{t("hero.eyebrow")}</p>
            <h1 className="lp-hero__title">
              <Trans t={t} i18nKey="hero.title" components={{ em: <em /> }} />
            </h1>
            <p className="lp-hero__sub">{t("hero.sub")}</p>

            <div className="lp-hero__cta">
              <Link to="/signup" className="lp-btn lp-btn--sun">
                {t("hero.primaryCta")}
              </Link>
              <Link to="/login" className="lp-btn lp-btn--ghost">
                {t("hero.secondaryCta")}
              </Link>
            </div>

            <div className="lp-strip">
              <span className="lp-strip__dot" />
              <span className="lp-strip__hi">LIS</span>
              <span>→</span>
              <span className="lp-strip__hi">MAR</span>
              <span className="lp-strip__sep">·</span>
              <span>{t("hero.stripHour")}</span>
              <span className="lp-strip__sep">·</span>
              <span>{t("hero.stripSaved")}</span>
            </div>
          </div>
        </div>

        <span className="lp-scroll" aria-hidden>
          {t("scroll")}
          <span className="lp-scroll__line" />
        </span>
      </section>

      {/* --- Content (opaque wrapper over the globe) --- */}
      <div className="lp-content">
        {/* Features */}
        <section className="lp-section lp-features">
          <div className="lp-section__head">
            <p className="lp-eyebrow">{t("features.eyebrow")}</p>
            <h2 className="lp-section__title">{t("features.title")}</h2>
            <p className="lp-section__lead">{t("features.lead")}</p>
          </div>

          <div className="lp-features__grid">
            {features.map((feature) => (
              <article key={feature.title} className="lp-card">
                <span className="lp-card__stamp">{feature.stamp}</span>
                <h3 className="lp-card__title">{feature.title}</h3>
                <p className="lp-card__body">{feature.body}</p>
              </article>
            ))}
          </div>
        </section>

        <div className="lp-rule" />

        {/* How it works */}
        <section className="lp-section lp-steps">
          <div className="lp-steps__wrap">
            <div className="lp-section__head">
              <p className="lp-eyebrow">{t("steps.eyebrow")}</p>
              <h2 className="lp-section__title">{t("steps.title")}</h2>
            </div>

            <ol className="lp-steps__list">
              {steps.map((step) => (
                <li key={step.no} className="lp-step">
                  <span className="lp-step__no">{step.no}</span>
                  <h3 className="lp-step__title">{step.title}</h3>
                  <p className="lp-step__body">{step.body}</p>
                  <span className="lp-step__stamp">{step.stamp}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <div className="lp-rule" />

        {/* Sample atlas + journal entry */}
        <section className="lp-section lp-atlas">
          <div className="lp-section__head">
            <p className="lp-eyebrow">{t("atlas.eyebrow")}</p>
            <h2 className="lp-section__title">{t("atlas.title")}</h2>
          </div>

          <div className="lp-atlas__grid">
            <div className="lp-atlas__stats">
              {stats.map((stat) => (
                <div key={stat.label} className="lp-stat">
                  <div className="lp-stat__value">{stat.value}</div>
                  <div className="lp-stat__label">{stat.label}</div>
                </div>
              ))}
            </div>

            <figure className="lp-journal">
              <figcaption className="lp-journal__date">{t("atlas.journalDate")}</figcaption>
              {/* Quotes are part of the translation string, not markup: Russian uses «guillemets»,
                  English uses “curly quotes”, and a hardcoded pair put English quotes around
                  Russian text. */}
              <blockquote className="lp-journal__quote">{t("atlas.journalQuote")}</blockquote>
              <div className="lp-journal__from">— {t("atlas.journalFrom")}</div>
            </figure>
          </div>
        </section>
      </div>

      {/* --- CTA footer --- */}
      <footer className="lp-foot">
        <div className="lp-foot__inner">
          <p className="lp-eyebrow">{BRAND}</p>
          <h2 className="lp-foot__title">{t("footer.title")}</h2>
          <p className="lp-foot__sub">{t("footer.sub")}</p>

          <div className="lp-foot__cta">
            <Link to="/signup" className="lp-btn lp-btn--sun">
              {t("footer.primaryCta")}
            </Link>
            <Link to="/login" className="lp-btn lp-btn--ghost">
              {t("footer.secondaryCta")}
            </Link>
          </div>

          <div className="lp-foot__meta">
            <span>© {BRAND}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
