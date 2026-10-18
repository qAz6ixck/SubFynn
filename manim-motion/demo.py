from manim import *

class TitleIntro(Scene):
    def construct(self):
        # Background gradient effect / text
        title = Text("MOTION GRAPHICS", font_size=56, weight=BOLD, color=YELLOW)
        subtitle = Text("Powered by Manim Community Edition", font_size=26, color=BLUE_B)
        subtitle.next_to(title, DOWN, buff=0.4)

        box = SurroundingRectangle(title, buff=0.35, color=TEAL_C, corner_radius=0.15)
        
        # Animations
        self.play(Create(box), run_time=1.2)
        self.play(Write(title), run_time=1.4)
        self.play(FadeIn(subtitle, shift=UP * 0.4), run_time=0.9)
        self.wait(0.5)
        self.play(Indicate(title, scale_factor=1.08, color=GOLD))
        self.wait(1.5)
