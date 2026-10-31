"""High-performance Object-Pooled FX and Particle Subsystem for Bloxorz 3D.

Maintains pre-allocated Entity pools for zero-garbage collection, preventing
memory fragmentation and frame-time spikes in the Ursina game loop.
"""

import math
import random
from typing import List, Optional, Sequence
from ursina import Entity, Vec3, color, curve, time

from bloxorz.config import CONFIG
from bloxorz.ui.theme import Palette, ColorToken


class _GhostItem:
    """Pre-allocated ghost echo block mesh."""
    __slots__ = ("entity", "active", "alpha", "fade_speed", "r", "g", "b")

    def __init__(self, parent: Optional[Entity] = None):
        self.entity = Entity(
            parent=parent,
            name="fx_ghost",
            model='cube',
            unlit=True,
            enabled=False,
        )
        self.active: bool = False
        self.alpha: float = 0.0
        self.fade_speed: float = 3.0
        self.r: float = 1.0
        self.g: float = 1.0
        self.b: float = 1.0


class _RingItem:
    """Pre-allocated expanding planar shockwave ripple."""
    __slots__ = ("entity", "active", "elapsed", "duration", "max_radius", "r", "g", "b")

    def __init__(self, parent: Optional[Entity] = None):
        self.entity = Entity(
            parent=parent,
            name="fx_shockwave_ring",
            model='quad',
            rotation_x=90,
            unlit=True,
            enabled=False,
        )
        self.active: bool = False
        self.elapsed: float = 0.0
        self.duration: float = 0.25
        self.max_radius: float = 1.8
        self.r: float = 0.22
        self.g: float = 0.74
        self.b: float = 0.97


class _ParticleItem:
    """Pre-allocated physics particle for debris, sparks, and confetti."""
    __slots__ = (
        "entity", "active", "vel", "rot_vel", "base_scale",
        "life", "max_life", "gravity", "r", "g", "b", "is_confetti",
        "is_ember", "drag"
    )

    def __init__(self, parent: Optional[Entity] = None):
        self.entity = Entity(
            parent=parent,
            name="fx_particle",
            model='cube',
            unlit=True,
            enabled=False,
        )
        self.active: bool = False
        self.vel = Vec3(0, 0, 0)
        self.rot_vel = Vec3(0, 0, 0)
        self.base_scale: float = 0.08
        self.life: float = 0.0
        self.max_life: float = 1.0
        self.gravity: float = 9.8
        self.r: float = 1.0
        self.g: float = 1.0
        self.b: float = 1.0
        self.is_confetti: bool = False
        self.is_ember: bool = False
        self.drag: float = 0.0


class _AmbientDustItem:
    """Pre-allocated ambient atmospheric dust / molten magma ember."""
    __slots__ = ("entity", "base_pos", "phase_x", "phase_y", "phase_z", "speed", "amp", "alpha_base", "r", "g", "b")

    def __init__(self, parent: Optional[Entity] = None):
        self.entity = Entity(
            parent=parent,
            name="fx_ambient_dust",
            model='cube',
            unlit=True,
            enabled=False,
        )
        self.base_pos = Vec3(0, 0, 0)
        self.phase_x: float = random.uniform(0, math.tau)
        self.phase_y: float = random.uniform(0, math.tau)
        self.phase_z: float = random.uniform(0, math.tau)
        self.speed: float = random.uniform(0.4, 0.9)
        self.amp: float = random.uniform(0.3, 0.7)
        self.alpha_base: float = random.uniform(0.25, 0.55)
        self.r: float = 1.0
        self.g: float = 0.35
        self.b: float = 0.12


class FXManager(Entity):
    """Singleton-style VFX Engine managing pre-allocated particle & animation pools.

    Inherits from Ursina Entity to synchronize with engine delta-time loop.
    All allocations are performed in __init__ to guarantee zero GC during gameplay.
    """

    POOL_GHOSTS = 4
    POOL_RINGS = 4
    POOL_PARTICLES = 40
    POOL_AMBIENT = 16

    _instance: Optional["FXManager"] = None

    def __init__(self, **kwargs):
        super().__init__(name="fx_manager_core", **kwargs)
        FXManager._instance = self

        # 1. Pre-allocate pools parented to self for consistent board-local coordinates
        self._ghosts: List[_GhostItem] = [_GhostItem(parent=self) for _ in range(self.POOL_GHOSTS)]
        self._rings: List[_RingItem] = [_RingItem(parent=self) for _ in range(self.POOL_RINGS)]
        self._particles: List[_ParticleItem] = [_ParticleItem(parent=self) for _ in range(self.POOL_PARTICLES)]
        self._ambient: List[_AmbientDustItem] = [_AmbientDustItem(parent=self) for _ in range(self.POOL_AMBIENT)]

        # Ambient dust state
        self._ambient_enabled: bool = False
        self._ambient_center = Vec3(0, 0, 0)
        self._ambient_bounds = 12.0
        self._ambient_time: float = 0.0

    @classmethod
    def get_instance(cls) -> "FXManager":
        """Returns active singleton instance or instantiates one."""
        if cls._instance is None:
            cls._instance = FXManager()
        return cls._instance

    # -------------------------------------------------------------------------
    # Core Spawner Methods
    # -------------------------------------------------------------------------

    def spawn_ghost(
        self,
        position: Vec3,
        rotation: Vec3,
        scale: Vec3,
        token: Optional[ColorToken] = None,
        alpha: Optional[float] = None,
    ) -> None:
        """Emits a semi-transparent ghost echo at previous roll location."""
        if not getattr(CONFIG.animation, "ghost_trail_enabled", True):
            return

        tok = token or Palette.GHOST_TRAIL
        init_alpha = alpha if alpha is not None else getattr(CONFIG.animation, "ghost_alpha", 0.25)
        fade_speed = getattr(CONFIG.animation, "ghost_fade_speed", 3.0)

        # Find first inactive ghost or recycle oldest
        target: Optional[_GhostItem] = None
        for g in self._ghosts:
            if not g.active:
                target = g
                break
        if target is None:
            target = self._ghosts[0]

        target.active = True
        target.alpha = init_alpha
        target.fade_speed = fade_speed
        target.r = tok.r
        target.g = tok.g
        target.b = tok.b

        target.entity.position = position
        target.entity.rotation = rotation
        target.entity.scale = scale
        target.entity.color = color.rgba(tok.r, tok.g, tok.b, init_alpha)
        target.entity.enabled = True

    def spawn_shockwave(
        self,
        position: Vec3,
        token: Optional[ColorToken] = None,
        max_radius: float = 1.8,
        duration: float = 0.35,
    ) -> None:
        """Spawns an expanding serene water ripple across the surface."""
        tok = token or Palette.SHOCKWAVE_RING

        target: Optional[_RingItem] = None
        for r in self._rings:
            if not r.active:
                target = r
                break
        if target is None:
            target = self._rings[0]

        target.active = True
        target.elapsed = 0.0
        target.duration = max(0.05, duration)
        target.max_radius = max_radius
        target.r = tok.r
        target.g = tok.g
        target.b = tok.b

        # Place gently above surface (Y + 0.015)
        target.entity.position = Vec3(position.x, position.y + 0.015, position.z)
        target.entity.rotation = Vec3(90, 0, 0)
        target.entity.scale = Vec3(0.05, 0.05, 0.05)
        target.entity.color = color.rgba(tok.r, tok.g, tok.b, 0.35)
        target.entity.enabled = True

    def spawn_particles(
        self,
        position: Vec3,
        count: int = 8,
        token: Optional[ColorToken] = None,
        tokens: Optional[Sequence[ColorToken]] = None,
        speed: float = 2.5,
        spread: float = 1.0,
        gravity: float = 9.8,
        life: float = 0.5,
        scale: float = 0.07,
        upward_bias: float = 1.2,
    ) -> None:
        """Emits a burst of physics particles with random velocities."""
        pool_tokens = list(tokens) if tokens else ([token] if token else [Palette.VICTORY_GOLD])
        spawned = 0

        for p in self._particles:
            if spawned >= count:
                break
            if not p.active:
                p.active = True
                p.is_confetti = False
                p.is_ember = False
                p.base_scale = scale * random.uniform(0.8, 1.25)
                p.life = life * random.uniform(0.75, 1.25)
                p.max_life = p.life
                p.gravity = gravity

                tok = random.choice(pool_tokens)
                p.r = tok.r
                p.g = tok.g
                p.b = tok.b

                # Directional burst
                ang = random.uniform(0, math.tau)
                rad = random.uniform(0.2, 1.0) * spread
                vx = math.cos(ang) * rad * speed
                vz = math.sin(ang) * rad * speed
                vy = (random.uniform(0.4, 1.2) + upward_bias) * speed
                p.vel = Vec3(vx, vy, vz)

                p.rot_vel = Vec3(
                    random.uniform(-360, 360),
                    random.uniform(-360, 360),
                    random.uniform(-360, 360),
                )

                p.entity.position = position
                p.entity.rotation = Vec3(random.uniform(0, 360), random.uniform(0, 360), 0)
                p.entity.scale = Vec3(p.base_scale, p.base_scale, p.base_scale)
                p.entity.color = color.rgba(tok.r, tok.g, tok.b, tok.a)
                p.entity.enabled = True
                spawned += 1

    def spawn_ember_ash(
        self,
        position: Vec3,
        count: int = 1,
        tokens: Optional[Sequence[ColorToken]] = None,
        outward_dir: Optional[Vec3] = None,
        speed: float = 3.2,
        life: float = 0.45,
    ) -> None:
        """Spawns radiant incandescent fire ash sparks that streak outward, cool to magma amber, and dissipate."""
        pool_tokens = list(tokens) if tokens else [Palette.EMBER_ASH, Palette.EMBER_ASH_GLOW, Palette.EMBER_ASH_SPARK]
        spawned = 0

        for p in self._particles:
            if spawned >= count:
                break
            if not p.active:
                p.active = True
                p.is_confetti = False
                p.is_ember = True
                p.drag = 4.5
                # Radiant spark mote scale
                p.base_scale = random.uniform(0.020, 0.035)
                p.life = life * random.uniform(0.85, 1.20)
                p.max_life = p.life
                p.gravity = 1.2

                tok = random.choice(pool_tokens)
                p.r = tok.r
                p.g = tok.g
                p.b = tok.b

                # Outward burst velocity
                if outward_dir is not None:
                    ang_jitter = random.uniform(-0.35, 0.35)
                    cos_j = math.cos(ang_jitter)
                    sin_j = math.sin(ang_jitter)
                    vx = (outward_dir.x * cos_j - outward_dir.z * sin_j) * speed * random.uniform(0.8, 1.3)
                    vz = (outward_dir.x * sin_j + outward_dir.z * cos_j) * speed * random.uniform(0.8, 1.3)
                else:
                    ang = random.uniform(0, math.tau)
                    sp = speed * random.uniform(0.8, 1.3)
                    vx = math.cos(ang) * sp
                    vz = math.sin(ang) * sp

                vy = random.uniform(0.6, 1.6)
                p.vel = Vec3(vx, vy, vz)
                p.rot_vel = Vec3(0, 0, 0)

                p.entity.position = position
                p.entity.rotation = Vec3(0, 0, 0)
                p.entity.scale = Vec3(p.base_scale, p.base_scale, p.base_scale)
                # Birth: Brilliant incandescent white-gold heat
                p.entity.color = color.rgba(1.0, 0.96, 0.82, 1.0)
                p.entity.enabled = True
                spawned += 1

    def spawn_confetti(self, position: Vec3, count: int = 36) -> None:
        """Celebratory festive burst for stage completion."""
        tokens = [Palette.VICTORY_GOLD, Palette.VICTORY_CYAN, Palette.VICTORY_WHITE]
        spawned = 0

        for p in self._particles:
            if spawned >= count:
                break
            if not p.active:
                p.active = True
                p.is_confetti = True
                p.is_ember = False
                tok = tokens[spawned % len(tokens)]
                p.base_scale = random.uniform(0.08, 0.14)
                p.life = random.uniform(1.2, 1.8)
                p.max_life = p.life
                p.gravity = 4.5  # Lower gravity for fluttering confetti
                p.r = tok.r
                p.g = tok.g
                p.b = tok.b

                ang = random.uniform(0, math.tau)
                rad = random.uniform(0.5, 1.8)
                p.vel = Vec3(
                    math.cos(ang) * rad * 2.2,
                    random.uniform(4.0, 7.5),
                    math.sin(ang) * rad * 2.2,
                )
                p.rot_vel = Vec3(
                    random.uniform(-400, 400),
                    random.uniform(-400, 400),
                    random.uniform(-200, 200),
                )

                p.entity.position = Vec3(position.x, position.y + 0.5, position.z)
                p.entity.rotation = Vec3(random.uniform(0, 360), random.uniform(0, 360), 0)
                p.entity.scale = Vec3(p.base_scale, p.base_scale * 0.4, p.base_scale)
                p.entity.color = color.rgba(tok.r, tok.g, tok.b, 1.0)
                p.entity.enabled = True
                spawned += 1

    def spawn_teleport_sparks(self, position: Vec3, count: int = 16) -> None:
        """Sparks emitted during teleport split and merge operations."""
        self.spawn_particles(
            position=position,
            count=count,
            token=Palette.TELEPORT_ENERGY,
            speed=3.2,
            spread=1.2,
            gravity=6.0,
            life=0.45,
            scale=0.06,
            upward_bias=0.8,
        )

    def spawn_crumble_debris(self, position: Vec3, count: int = 12) -> None:
        """Orange terracotta fragments when a fragile tile collapses."""
        self.spawn_particles(
            position=position,
            count=count,
            token=Palette.CRUMBLE_FRAGMENT,
            speed=1.8,
            spread=0.8,
            gravity=12.0,
            life=0.6,
            scale=0.08,
            upward_bias=0.2,
        )

    # -------------------------------------------------------------------------
    # Ambient Dust Atmosphere
    # -------------------------------------------------------------------------

    def setup_ambient_dust(self, center: Vec3, bounds: float = 12.0) -> None:
        """Initializes floating atmospheric molten embers around stage bounds."""
        self._ambient_center = center
        self._ambient_bounds = bounds
        ember_tokens = [Palette.MAGMA_EMBER, Palette.MAGMA_SPARK, Palette.LAVA_NEON_PINK]

        for dust in self._ambient:
            dust.base_pos = Vec3(
                center.x + random.uniform(-bounds, bounds),
                center.y + random.uniform(-1.5, 3.5),
                center.z + random.uniform(-bounds, bounds),
            )
            dust.entity.position = dust.base_pos
            s = random.uniform(0.035, 0.065)
            dust.entity.scale = Vec3(s, s, s)
            tok = random.choice(ember_tokens)
            dust.r, dust.g, dust.b = tok.r, tok.g, tok.b
            dust.entity.color = color.rgba(dust.r, dust.g, dust.b, dust.alpha_base)
            dust.entity.enabled = True

        self._ambient_enabled = True

    def set_ambient_enabled(self, enabled: bool) -> None:
        """Enables or disables ambient dust rendering."""
        self._ambient_enabled = enabled
        for dust in self._ambient:
            dust.entity.enabled = enabled

    # -------------------------------------------------------------------------
    # Clear & Reset
    # -------------------------------------------------------------------------

    def clear_all(self) -> None:
        """Deactivates all active transient VFX entities back into the dormant pool."""
        for g in self._ghosts:
            g.active = False
            g.entity.enabled = False

        for r in self._rings:
            r.active = False
            r.entity.enabled = False

        for p in self._particles:
            p.active = False
            p.entity.enabled = False

    # -------------------------------------------------------------------------
    # Per-Frame Delta-Time Engine Update Loop
    # -------------------------------------------------------------------------

    def update(self) -> None:
        """Advances physics, fades, and scale transforms for all active effects."""
        dt = time.dt
        if dt <= 0.0:
            return

        # 1. Update Ghosts (Fade Alpha)
        for g in self._ghosts:
            if g.active:
                g.alpha -= g.fade_speed * dt
                if g.alpha <= 0.0:
                    g.active = False
                    g.entity.enabled = False
                else:
                    g.entity.color = color.rgba(g.r, g.g, g.b, g.alpha)

        # 2. Update Shockwave Rings (Expand Scale & Fade Alpha)
        for r in self._rings:
            if r.active:
                r.elapsed += dt
                t = min(1.0, r.elapsed / r.duration)
                if t >= 1.0:
                    r.active = False
                    r.entity.enabled = False
                else:
                    rad = r.max_radius * 2.0 * curve.out_sine(t)
                    r.entity.scale = Vec3(rad, rad, 1.0)
                    alpha = (1.0 - t) * 0.35
                    r.entity.color = color.rgba(r.r, r.g, r.b, alpha)

        # 3. Update Particles (Kinematics, Gravity, Scale Decay, Thermal Cooling)
        for p in self._particles:
            if p.active:
                p.life -= dt
                if p.life <= 0.0:
                    p.active = False
                    p.entity.enabled = False
                else:
                    progress = 1.0 - (p.life / p.max_life)

                    if getattr(p, "is_ember", False):
                        drag_factor = max(0.0, 1.0 - p.drag * dt)
                        p.vel.x *= drag_factor
                        p.vel.z *= drag_factor
                        p.vel.y -= p.gravity * dt
                        p.vel.y += 0.65 * dt  # Thermal buoyancy draft from heat
                        p.entity.position += p.vel * dt

                        # Thermal cooling gradient: White-gold spark -> Molten magma amber -> Smoldering ash
                        if progress < 0.28:
                            t_col = progress / 0.28
                            r = 1.0
                            g = 0.96 - 0.14 * t_col
                            b = 0.82 - 0.62 * t_col
                            alpha = 1.0
                        elif progress < 0.65:
                            t_col = (progress - 0.28) / 0.37
                            r = 1.0
                            g = 0.82 - 0.45 * t_col
                            b = 0.20 - 0.15 * t_col
                            alpha = 0.95 - 0.15 * t_col
                        else:
                            t_col = (progress - 0.65) / 0.35
                            r = 1.0 - 0.60 * t_col
                            g = 0.37 - 0.14 * t_col
                            b = 0.05 + 0.15 * t_col
                            alpha = max(0.0, (1.0 - t_col) * 0.80)

                        speed_horiz = math.sqrt(p.vel.x * p.vel.x + p.vel.z * p.vel.z)
                        stretch = min(2.4, 1.0 + speed_horiz * 0.35)
                        s = p.base_scale * (1.0 - progress * 0.40)
                        p.entity.scale = Vec3(s * stretch, s * 0.80, s * stretch)
                        p.entity.color = color.rgba(r, g, b, alpha)

                    elif p.is_confetti:
                        p.vel.y -= p.gravity * dt
                        p.entity.position += p.vel * dt
                        p.entity.rotation += p.rot_vel * dt
                        s = p.base_scale * (1.0 - progress * 0.65)
                        alpha = max(0.0, 1.0 - progress)
                        p.entity.scale = Vec3(s, s * 0.35, s)
                        p.entity.color = color.rgba(p.r, p.g, p.b, alpha)

                    else:
                        p.vel.y -= p.gravity * dt
                        p.entity.position += p.vel * dt
                        p.entity.rotation += p.rot_vel * dt
                        s = p.base_scale * (1.0 - progress * 0.65)
                        alpha = max(0.0, 1.0 - progress)
                        p.entity.scale = Vec3(s, s, s)
                        p.entity.color = color.rgba(p.r, p.g, p.b, alpha)

        # 4. Update Ambient Magma Embers
        if self._ambient_enabled:
            self._ambient_time += dt
            t = self._ambient_time

            for dust in self._ambient:
                dust.base_pos.y += 0.25 * dt
                if hasattr(self, "_ambient_center") and self._ambient_center:
                    if dust.base_pos.y > self._ambient_center.y + 4.5:
                        dust.base_pos.y = self._ambient_center.y - 1.6

                dx = math.sin(t * dust.speed + dust.phase_x) * dust.amp
                dy = math.sin(t * dust.speed * 0.7 + dust.phase_y) * (dust.amp * 0.4)
                dz = math.cos(t * dust.speed * 0.8 + dust.phase_z) * dust.amp
                dust.entity.position = dust.base_pos + Vec3(dx, dy, dz)

                alpha = dust.alpha_base * (0.75 + 0.25 * math.sin(t * 1.8 + dust.phase_y))
                dust.entity.color = color.rgba(dust.r, dust.g, dust.b, alpha)
