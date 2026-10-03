import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { projects, studio } from "./content";
import "./style.css";

gsap.registerPlugin(useGSAP, ScrollTrigger);
const Pavilion = lazy(() => import("./Pavilion").then((module) => ({ default: module.Pavilion })));
function DeferredPavilion({ reduced }: { reduced: boolean }) {
  const holder = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(false);
  useEffect(() => {
    if (!holder.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setNear(true);
          observer.disconnect();
        }
      },
      { rootMargin: "400px" },
    );
    observer.observe(holder.current);
    return () => observer.disconnect();
  }, []);
  const fallback = (
    <section className="pavilion-section">
      <div className="section-label">03 / THE DAYLIGHT LAB</div>
      <div className="pavilion-top">
        <h2>
          Same place.
          <br />
          Different light.
        </h2>
        <p>
          A courtyard shaped by sunlight.
          <br />
          The interactive architectural study loads as you approach.
        </p>
      </div>
      <div className="pavilion-stage">
        <img
          src="/images/solaris-hero-mobile.webp"
          alt="Sculptural courtyard architecture with an open skylight"
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>
    </section>
  );
  return (
    <div ref={holder}>
      {near ? (
        <Suspense fallback={fallback}>
          <Pavilion reduced={reduced} />
        </Suspense>
      ) : (
        fallback
      )}
    </div>
  );
}
function App() {
  const [route, setRoute] = useState(location.hash.slice(1) || "/");
  const [menu, setMenu] = useState(false);
  const [filter, setFilter] = useState("All");
  const [manual, setManual] = useState(false);
  const [os, setOs] = useState(matchMedia("(prefers-reduced-motion: reduce)").matches);
  const root = useRef<HTMLDivElement>(null);
  const reduced = manual || os;
  useEffect(() => {
    const fn = () => {
      setRoute(location.hash.slice(1) || "/");
      setMenu(false);
      window.scrollTo(0, 0);
    };
    addEventListener("hashchange", fn);
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenu(false);
    };
    addEventListener("keydown", handleEscape);
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setOs(media.matches);
    media.addEventListener("change", change);
    return () => {
      removeEventListener("hashchange", fn);
      removeEventListener("keydown", handleEscape);
      media.removeEventListener("change", change);
    };
  }, []);
  useEffect(() => {
    document.title = `${route === "/" ? "Designed around the light" : route === "/projects" ? "Selected spaces" : route === "/studio" ? "The studio" : route === "/contact" ? "Start a conversation" : projects.find((p) => route === `/projects/${p.id}`)?.title || "Page not found"} — SOLARIS`;
    root.current?.querySelector<HTMLElement>("main")?.focus({ preventScroll: true });
  }, [route]);
  useGSAP(
    () => {
      if (reduced) return;
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.from(".hero-line", { yPercent: 110, duration: 1.2, stagger: 0.14 })
        .from(".sun-mark", { rotation: -70, scale: 0.6, duration: 1.4 }, 0.15)
        .from(
          ".hero-photo",
          { clipPath: "inset(15% 10% 15% 10%)", scale: 1.04, duration: 1.5 },
          0.2,
        )
        .from(".hero-meta", { y: 20, opacity: 0, duration: 0.7 }, 0.8);
      gsap.utils.toArray<HTMLElement>(".reveal").forEach(
        (el) =>
          void gsap.from(el, {
            y: 50,
            opacity: 0,
            duration: 0.9,
            scrollTrigger: { trigger: el, start: "top 88%", once: true },
          }),
      );
      gsap.utils.toArray<HTMLElement>(".project-photo").forEach(
        (el) =>
          void gsap.fromTo(
            el,
            { yPercent: -4 },
            {
              yPercent: 4,
              ease: "none",
              scrollTrigger: {
                trigger: el.parentElement,
                start: "top bottom",
                end: "bottom top",
                scrub: 1,
              },
            },
          ),
      );
    },
    { scope: root, dependencies: [route, reduced], revertOnUpdate: true },
  );
  const selected = projects.find((p) => route === `/projects/${p.id}`);
  const cards = (all: boolean) => (
    <div className="project-grid">
      {projects
        .filter((p) => filter === "All" || !all || p.category === filter)
        .slice(0, all ? 4 : 2)
        .map((p, i) => (
          <a className={`project-card reveal project-${i}`} href={`#/projects/${p.id}`} key={p.id}>
            <div className="project-image">
              <img
                className="project-photo"
                src={p.image}
                srcSet={`${p.image.replace(".webp", "-mobile.webp")} 768w, ${p.image} 1536w`}
                sizes="(max-width:600px) 88vw, 46vw"
                alt={`${p.title}: conceptual architecture with sculptural forms and natural light`}
                loading="lazy"
              />
              <span className="card-arrow">↗</span>
              <span className="image-index">0{i + 1}</span>
            </div>
            <div className="project-caption">
              <h3>{p.title}</h3>
              <span>
                {p.category}
                <br />
                {p.location} / {p.year}
              </span>
            </div>
          </a>
        ))}
    </div>
  );
  return (
    <div ref={root}>
      <header>
        <a className="wordmark" href="#/" aria-label="SOLARIS home">
          SOLARIS
        </a>
        <button
          className="menu-button"
          type="button"
          aria-expanded={menu}
          aria-controls="navigation"
          onClick={() => setMenu(!menu)}
        >
          {menu ? "Close −" : "Menu +"}
        </button>
        <nav id="navigation" className={menu ? "is-open" : ""} aria-label="Main navigation">
          {[
            ["Projects", "/projects"],
            ["Studio", "/studio"],
            ["Let’s talk", "/contact"],
          ].map(([text, path]) => (
            <a key={path} href={`#${path}`} aria-current={route === path ? "page" : undefined}>
              {text}
              {path === "/contact" ? " ↗" : ""}
            </a>
          ))}
        </nav>
      </header>
      <main tabIndex={-1}>
        {route === "/" ? (
          <>
            <section className="hero">
              <div className="hero-top">
                <h1 className="hero-title">
                  <span className="line-mask">
                    <span className="hero-line">Designed </span>
                  </span>
                  <span className="line-mask">
                    <span className="hero-line">around </span>
                  </span>
                  <span className="line-mask">
                    <span className="hero-line">
                      the light<span className="blue-dot">.</span>
                    </span>
                  </span>
                </h1>
                <div className="sun-mark" aria-hidden="true">
                  ✳
                </div>
                <div className="hero-meta">
                  <p>
                    Architecture for
                    <br />a brighter everyday.
                  </p>
                  <span>
                    INDEPENDENT CONCEPT STUDIO
                    <br />
                    EST. 2026 / SOUTH AFRICA
                  </span>
                  <a href="#/projects">Explore our spaces ↘</a>
                </div>
              </div>
              <div className="hero-photo">
                <picture>
                  <source media="(max-width:600px)" srcSet="/images/solaris-hero-mobile.webp" />
                  <img
                    src="/images/solaris-hero.webp"
                    alt="Sunlit sculptural contemporary architecture surrounding an open courtyard"
                    fetchPriority="high"
                  />
                </picture>
                <div className="photo-label">
                  SUN COURT / RESIDENTIAL STUDY
                  <br />
                  01 — FINDING THE OPEN SKY
                </div>
                <div className="photo-coordinate">
                  33°55′ S<br />
                  18°25′ E
                </div>
              </div>
            </section>
            <section className="intro reveal">
              <div className="section-label">01 / OUR PERSPECTIVE</div>
              <h2>{studio.statement}</h2>
              <div className="intro-copy">
                <p>{studio.description}</p>
                <a className="text-link" href="#/studio">
                  Meet the studio ↗
                </a>
              </div>
            </section>
            <section className="work">
              <div className="work-heading reveal">
                <div>
                  <div className="section-label">02 / SELECTED SPACES</div>
                  <h2>
                    Room for
                    <br />
                    possibility.
                  </h2>
                </div>
                <a className="text-link" href="#/projects">
                  View all projects ↗
                </a>
              </div>
              {cards(false)}
            </section>
            <DeferredPavilion reduced={reduced} />
            <section className="closing reveal">
              <span>A LITTLE LIGHT GOES A LONG WAY.</span>
              <h2>
                What could
                <br />
                we open up?
              </h2>
              <a href="#/contact">Let’s make space ↗</a>
            </section>
          </>
        ) : route === "/projects" ? (
          <section className="page-section">
            <div className="section-label">THE PROJECT INDEX / CONCEPT STUDIES</div>
            <h1 className="page-title">
              Open
              <br />
              possibilities<span className="blue-dot">.</span>
            </h1>
            <fieldset className="filters" aria-label="Project category">
              {["All", "Residential", "Cultural", "Interiors"].map((f) => (
                <button
                  type="button"
                  key={f}
                  aria-pressed={filter === f}
                  onClick={() => setFilter(f)}
                >
                  {f}
                  {f === "All" ? ` (${projects.length})` : ""}
                </button>
              ))}
            </fieldset>
            {cards(true)}
          </section>
        ) : selected ? (
          <article className="detail">
            <a className="text-link" href="#/projects">
              ← Back to projects
            </a>
            <div className="detail-heading">
              <h1>{selected.title}</h1>
              <p>
                {selected.category} / {selected.location}
                <br />
                CONCEPT STUDY / {selected.year}
              </p>
            </div>
            <img
              className="detail-image"
              src={selected.image}
              srcSet={`${selected.image.replace(".webp", "-mobile.webp")} 768w, ${selected.image} 1536w`}
              sizes="92vw"
              alt={`Architectural concept illustrating ${selected.title}`}
            />
            <div className="detail-copy reveal">
              <h2>{selected.intro}</h2>
              <p>{selected.text}</p>
            </div>
            <div className="detail-facts">
              <span>
                Status
                <br />
                <strong>Unbuilt concept</strong>
              </span>
              <span>
                Approach
                <br />
                <strong>Light-led design</strong>
              </span>
              <span>
                Materials
                <br />
                <strong>Concrete / ash / glass</strong>
              </span>
            </div>
            <a
              className="next-project"
              href={`#/projects/${projects[(projects.indexOf(selected) + 1) % projects.length]?.id}`}
            >
              Next possibility <span>↗</span>
            </a>
          </article>
        ) : route === "/studio" ? (
          <section className="page-section studio">
            <div className="section-label">THE STUDIO / A SHARED OUTLOOK</div>
            <h1 className="page-title">
              Look towards
              <br />
              the light<span className="blue-dot">.</span>
            </h1>
            <div className="studio-statement">
              <span className="studio-sun" aria-hidden="true">
                ✳
              </span>
              <div>
                <h2>{studio.statement}</h2>
                <p>{studio.description}</p>
              </div>
            </div>
            <div className="principles">
              {[
                [
                  "01",
                  "Listen first.",
                  "We start with how a place will be lived in. The daily rituals, the small pleasures and the things that need room to grow.",
                ],
                [
                  "02",
                  "Follow the light.",
                  "Orientation, shadow and openness shape every decision. We explore the building as a changing experience, from morning to evening.",
                ],
                [
                  "03",
                  "Make it last.",
                  "Honest materials, generous proportions and adaptable spaces. Thoughtful architecture leaves room for the future.",
                ],
              ].map(([n, t, d]) => (
                <div className="reveal" key={n}>
                  <span>{n}</span>
                  <h3>{t}</h3>
                  <p>{d}</p>
                </div>
              ))}
            </div>
            <a className="next-project" href="#/contact">
              Begin with a conversation ↗
            </a>
          </section>
        ) : route === "/contact" ? (
          <Contact />
        ) : (
          <section className="page-section">
            <h1 className="page-title">An unopened door.</h1>
            <p>This page does not exist.</p>
            <a href="#/">Return to the light ↗</a>
          </section>
        )}
      </main>
      <footer>
        <div className="footer-top">
          <a href="#/contact">
            Good spaces start
            <br />
            with a conversation. ↗
          </a>
          <button type="button" aria-pressed={manual} onClick={() => setManual(!manual)}>
            {manual ? "Motion paused" : "Pause motion"}
            {os ? " / system reduced motion" : ""}
          </button>
        </div>
        <div className="footer-logo" aria-hidden="true">
          SOLARIS
        </div>
        <div className="footer-bottom">
          <span>© 2026 SOLARIS / FICTIONAL PORTFOLIO CONCEPT</span>
          <p>
            All projects are fictional design studies. Images illustrate a concept and are not
            completed client commissions.
          </p>
          <a href="#/studio">Made around the light ↗</a>
        </div>
      </footer>
    </div>
  );
}
function Contact() {
  const [type, setType] = useState("New home");
  const [timing, setTiming] = useState("Exploring possibilities");
  const [priority, setPriority] = useState("Natural light");
  const [ready, setReady] = useState(false);
  const brief = `SOLARIS — local project brief\nProject: ${type}\nTiming: ${timing}\nPriority: ${priority}\n\nFictional portfolio demo. No personal information collected; nothing has been sent.`;
  const download = () => {
    const url = URL.createObjectURL(new Blob([brief], { type: "text/plain" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "solaris-project-brief.txt";
    a.click();
    URL.revokeObjectURL(url);
    setReady(true);
  };
  return (
    <section className="page-section contact">
      <div className="section-label">LET’S TALK / START WITH POSSIBILITY</div>
      <h1 className="page-title">
        Your next
        <br />
        chapter<span className="blue-dot">.</span>
      </h1>
      <div className="contact-grid">
        <div>
          <h2>
            Tell us what
            <br />
            you’re imagining.
          </h2>
          <p>
            Build a simple project brief to keep for yourself. This is a local demonstration: it
            collects no personal information and sends nothing.
          </p>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            download();
          }}
        >
          <label>
            01 / What kind of space?
            <select
              value={type}
              onChange={(e) => {
                setType(e.target.value);
                setReady(false);
              }}
            >
              {["New home", "Renovation", "Interior", "Cultural space"].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            02 / Where are you in the process?
            <select
              value={timing}
              onChange={(e) => {
                setTiming(e.target.value);
                setReady(false);
              }}
            >
              {["Exploring possibilities", "Planning this year", "Ready to begin"].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            03 / What matters most?
            <select
              value={priority}
              onChange={(e) => {
                setPriority(e.target.value);
                setReady(false);
              }}
            >
              {[
                "Natural light",
                "Connection to outdoors",
                "Flexible living",
                "Material character",
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <div className="brief-preview">
            <span>YOUR LOCAL BRIEF</span>
            <p>
              {type} · {timing}
              <br />
              {priority}
            </p>
          </div>
          <button className="download" type="submit">
            Download your brief ↗
          </button>
          <p role="status">
            {ready
              ? "Your brief is ready. Nothing was sent."
              : "A .txt file, saved to your device."}
          </p>
        </form>
      </div>
    </section>
  );
}
createRoot(document.getElementById("root") as HTMLElement).render(<App />);
