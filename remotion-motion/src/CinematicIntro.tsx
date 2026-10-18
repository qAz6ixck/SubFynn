import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export interface CinematicIntroProps {
  category?: string;
  title?: string;
  subtitle?: string;
}

export const CinematicIntro: React.FC<CinematicIntroProps> = ({
  category = "NEXT GENERATION CREATIVITY",
  title = "CYBER MOTION",
  subtitle = "EXPERIENCE THE FUTURE OF VISUAL STORYTELLING",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Subtle camera drift (slow push-in)
  const cameraScale = interpolate(frame, [0, durationInFrames], [1, 1.06], {
    extrapolateRight: "clamp",
  });

  // Background light sweep
  const lightX = interpolate(frame, [0, 80], [-20, 120]);
  const bgGlow = interpolate(frame, [0, 30], [0, 0.4], {
    extrapolateRight: "clamp",
  });

  // Category badge animation (starts at frame 10)
  const categorySpring = spring({
    frame: frame - 10,
    fps,
    config: { damping: 15 },
  });
  const categoryLetterSpacing = interpolate(categorySpring, [0, 1], [0.1, 0.35]);

  // Accent Line animation (starts at frame 40)
  const lineSpring = spring({
    frame: frame - 40,
    fps,
    config: { damping: 18, mass: 0.7 },
  });

  // Subtitle animation (starts at frame 55)
  const subtitleSpring = spring({
    frame: frame - 55,
    fps,
    config: { damping: 16 },
  });

  // Letters for main title (starts at frame 20)
  const letters = title.split("");

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#05070e",
        overflow: "hidden",
        fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      }}
    >
      {/* Background Ambience & Lighting */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `
            radial-gradient(circle at 50% 50%, rgba(56, 189, 248, ${bgGlow * 0.3}) 0%, transparent 60%),
            radial-gradient(circle at 80% 20%, rgba(139, 92, 246, ${bgGlow * 0.25}) 0%, transparent 50%),
            radial-gradient(circle at 20% 80%, rgba(236, 72, 153, ${bgGlow * 0.2}) 0%, transparent 50%)
          `,
        }}
      />

      {/* Cyber Grid Lines */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: 0.07,
          backgroundImage: `
            linear-gradient(to right, #38bdf8 1px, transparent 1px),
            linear-gradient(to bottom, #38bdf8 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
        }}
      />

      {/* Light Sweep Flare */}
      <div
        style={{
          position: "absolute",
          top: "40%",
          left: `${lightX}%`,
          width: "350px",
          height: "350px",
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(56,189,248,0.35) 0%, rgba(99,102,241,0.1) 40%, transparent 70%)",
          filter: "blur(40px)",
          pointerEvents: "none",
        }}
      />

      {/* Main Content with Camera Zoom */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${cameraScale})`,
          transformOrigin: "center center",
        }}
      >
        {/* Category Pill / Tag */}
        <div
          style={{
            opacity: categorySpring,
            transform: `translateY(${interpolate(categorySpring, [0, 1], [-20, 0])}px)`,
            color: "#38bdf8",
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: `${categoryLetterSpacing}em`,
            textTransform: "uppercase",
            marginBottom: 24,
            padding: "8px 24px",
            borderRadius: 9999,
            backgroundColor: "rgba(15, 23, 42, 0.75)",
            border: "1px solid rgba(56, 189, 248, 0.4)",
            boxShadow: "0 0 25px rgba(56, 189, 248, 0.25)",
            backdropFilter: "blur(12px)",
          }}
        >
          {category}
        </div>

        {/* Main Title (Kinetic Letter-by-Letter Stagger) */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            perspective: 1000,
            overflow: "hidden",
            padding: "10px 40px",
          }}
        >
          {letters.map((char, index) => {
            const letterSpring = spring({
              frame: frame - 20 - index * 2.2,
              fps,
              config: { damping: 14, mass: 0.8 },
            });

            const translateY = interpolate(letterSpring, [0, 1], [140, 0]);
            const rotateX = interpolate(letterSpring, [0, 1], [-65, 0]);
            const blur = interpolate(letterSpring, [0, 1], [20, 0]);
            const opacity = interpolate(letterSpring, [0, 0.5, 1], [0, 0.8, 1]);

            return (
              <span
                key={index}
                style={{
                  display: "inline-block",
                  fontSize: 110,
                  fontWeight: 900,
                  color: "#ffffff",
                  letterSpacing: "0.02em",
                  transform: `translateY(${translateY}px) rotateX(${rotateX}deg)`,
                  filter: `blur(${blur}px)`,
                  opacity,
                  textShadow:
                    "0 0 30px rgba(56, 189, 248, 0.6), 0 0 60px rgba(99, 102, 241, 0.4)",
                }}
              >
                {char === " " ? "\u00A0" : char}
              </span>
            );
          })}
        </div>

        {/* Glowing Divider Line */}
        <div
          style={{
            width: "600px",
            height: "2px",
            marginTop: 20,
            marginBottom: 24,
            background:
              "linear-gradient(90deg, transparent, #38bdf8 30%, #a855f7 70%, transparent)",
            transform: `scaleX(${lineSpring})`,
            boxShadow: "0 0 20px rgba(56, 189, 248, 0.8)",
          }}
        />

        {/* Subtitle */}
        <div
          style={{
            opacity: subtitleSpring,
            transform: `translateY(${interpolate(subtitleSpring, [0, 1], [25, 0])}px)`,
            color: "#94a3b8",
            fontSize: 24,
            fontWeight: 400,
            letterSpacing: "0.22em",
            textAlign: "center",
            maxWidth: 900,
            textShadow: "0 2px 10px rgba(0,0,0,0.8)",
          }}
        >
          {subtitle}
        </div>
      </div>

      {/* Corner Tech Accents */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 50,
          color: "rgba(56, 189, 248, 0.5)",
          fontSize: 13,
          fontFamily: "monospace",
          letterSpacing: "0.15em",
        }}
      >
        [REC] 00:0{Math.floor(frame / fps)}:{(frame % fps).toString().padStart(2, "0")}
      </div>
      <div
        style={{
          position: "absolute",
          top: 40,
          right: 50,
          color: "rgba(56, 189, 248, 0.5)",
          fontSize: 13,
          fontFamily: "monospace",
          letterSpacing: "0.15em",
        }}
      >
        RESOLUTION // 1920x1080 30FPS
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: 50,
          color: "rgba(148, 163, 184, 0.4)",
          fontSize: 12,
          fontFamily: "monospace",
        }}
      >
        AUDIO_SYNC: ACTIVE • ENGINE: REMOTION 4.0
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 40,
          right: 50,
          color: "rgba(148, 163, 184, 0.4)",
          fontSize: 12,
          fontFamily: "monospace",
        }}
      >
        CODE-DRIVEN MOTION GRAPHIC
      </div>
    </AbsoluteFill>
  );
};
