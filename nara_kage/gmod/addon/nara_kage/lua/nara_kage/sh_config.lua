-- Nara : Kagemane no Jutsu (manipulation des ombres) - reglages
-- Toutes les distances sont en unites Source (1 u = 1 pouce ; un joueur fait 72 u).

NARA = NARA or {}

NARA.Config = {
	-- ------------------------------------------------------------ deroulement
	-- Le lanceur met un genou a terre et forme le sceau, puis la camera passe
	-- dans la pointe de l'ombre et le joueur la dirige a la souris.
	WindupTime     = 1.15,  -- genou a terre + sceau avant que l'ombre parte (s)
	CamDiveTime    = 0.45,  -- plongee de la camera vers la pointe de l'ombre (s)
	SteerTime      = 13,    -- compteur affiche en bas de l'ecran (s)
	ShadowSpeed    = 250,   -- vitesse de la pointe (u/s)
	BoostSpeed     = 430,   -- en maintenant Avancer (Z / W)
	SlowSpeed      = 90,    -- en maintenant Reculer (S)
	TurnRate       = 170,   -- vitesse de virage max de l'ombre (degres/s)
	SerpentAngle   = 16,    -- l'ombre ondule d'elle-meme comme un serpent (degres de chaque cote, 0 = droite)
	SerpentPeriod  = 1.6,   -- duree d'une ondulation complete (s)
	MaxLength      = 3000,  -- longueur max de l'ombre (u)
	CatchRadius    = 24,    -- l'ombre attrape ce qui est a cette distance de sa pointe
	PossessTime    = 10,    -- duree de la possession une fois la cible prise (s)
	BreakDistance  = 3400,  -- le lien casse si le lanceur s'eloigne plus que ca
	RetractSpeed   = 1800,  -- vitesse de retour de l'ombre (u/s)
	Cooldown       = 4,     -- delai avant de pouvoir relancer (s)
	KneelLeg       = "R",   -- genou pose au sol : "R" (droit) ou "L" (gauche)
	AffectNPCs     = true,

	-- ------------------------------------------------------------ forme de l'ombre
	Width          = 7,     -- demi-largeur de la bande (la bande fait 14 u de large)
	WidthBreath    = 0.14,  -- la largeur varie doucement le long de l'ombre (0 = largeur fixe)
	TipLength      = 60,    -- longueur de la pointe effilee
	Color          = Color(7, 8, 11),   -- noir tres legerement froid, comme dans la video
	PoolLength     = 22,    -- demi-longueur de la flaque sous le lanceur (vers l'avant)
	PoolWidth      = 14,    -- demi-largeur de cette flaque
	PoolForward    = 6,     -- la flaque est decalee vers l'avant du lanceur
	TargetPool     = 16,    -- rayon de la flaque sous la cible prise

	-- ------------------------------------------------------------ camera dans la pointe
	CamHeight      = 14,    -- hauteur de l'oeil au-dessus du sol
	CamBack        = 24,    -- recul derriere la pointe : sa pointe effilee reste visible devant soi
	CamFOV         = 95,
	CamPitchMin    = -55,
	CamPitchMax    = 35,
	ScreenFX       = true,  -- image assombrie + vignettage pendant la vue depuis l'ombre

	-- Sons (chemins relatifs a sound/). Mets "" pour couper un son.
	Sounds = {
		Mudra   = "nara_kage/mudra.wav",
		Cast    = "nara_kage/cast.wav",
		Crawl   = "nara_kage/crawl_loop.wav",
		Bind    = "nara_kage/bind.wav",
		Release = "nara_kage/release.wav",
		Tick    = "nara_kage/tick.wav",
	},
}

-- Phases reseau de la technique
NARA.PH_NONE    = 0
NARA.PH_WINDUP  = 1   -- genou a terre + sceau
NARA.PH_STEER   = 2   -- l'ombre avance, dirigee depuis sa pointe (compteur 13 s)
NARA.PH_BOUND   = 3   -- cible prise : elle imite le lanceur
NARA.PH_RETRACT = 4   -- l'ombre revient au lanceur
