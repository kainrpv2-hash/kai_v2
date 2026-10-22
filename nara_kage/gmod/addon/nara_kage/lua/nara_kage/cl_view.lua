-- Nara : Kagemane no Jutsu - camera dans la pointe de l'ombre, compteur, effets d'ecran

NARA = NARA or {}
local C = NARA.Config
local Casts = NARA.Casts

local function ease(x) x = math.Clamp(x, 0, 1) return x * x * (3 - 2 * x) end

surface.CreateFont("NaraKage_Count", { font = "Roboto", size = ScreenScale(30), weight = 800, antialias = true })
surface.CreateFont("NaraKage_Label", { font = "Roboto", size = ScreenScale(7), weight = 600, antialias = true })
surface.CreateFont("NaraKage_Hint", { font = "Roboto", size = ScreenScale(5.5), weight = 500, antialias = true })

local VIGNETTE = Material("nara_kage/shadow_vignette")
local POOL = Material("nara_kage/shadow_pool")

-- ---------------------------------------------------------------- pose du corps

hook.Add("CalcMainActivity", "NaraKage_Kneel", function(ply)
	local rec = Casts[ply]
	if rec and (rec.wKneel or 0) > 0.01 then
		-- base debout immobile : la cinematique inverse fait le reste
		local seq = ply:LookupSequence("idle_all_01")
		if seq and seq >= 0 then return ACT_HL2MP_IDLE, seq end
	end
end)

hook.Add("PrePlayerDraw", "NaraKage_LockBody", function(ply)
	local rec = Casts[ply]
	if not rec or not (NARA.CasterFrozen(rec) or (rec.wKneel or 0) > 0.01) then return end
	-- le corps reste tourne vers la ou l'ombre est partie, meme si la camera tourne
	ply:SetRenderAngles(Angle(0, rec.lockYaw or ply:GetRenderAngles().y, 0))
	for _, p in ipairs({ "aim_yaw", "aim_pitch", "head_yaw", "head_pitch", "move_x", "move_y" }) do
		ply:SetPoseParameter(p, 0)
	end
	ply:InvalidateBoneCache()
end)

-- ---------------------------------------------------------------- camera

local camState = {}

local function TipCamera(rec, ply)
	-- au tout debut l'ombre n'a qu'un point : on part des pieds, dans la direction du lancer
	local pts = rec.drawPts or rec.path
	local tip = (pts and #pts > 0) and pts[#pts] or ply:GetPos()
	local back = (pts and #pts > 1) and pts[math.max(1, #pts - 4)] or tip
	local dir = tip - back
	dir.z = 0
	if dir:LengthSqr() < 1e-3 then dir = Angle(0, rec.lockYaw or 0, 0):Forward() end
	dir:Normalize()
	camState.dir = camState.dir and LerpVector(math.min(1, FrameTime() * 8), camState.dir, dir):GetNormalized() or dir
	return tip + Vector(0, 0, C.CamHeight) - camState.dir * C.CamBack
end

hook.Add("CalcView", "NaraKage_View", function(ply, origin, angles, fov)
	local rec = Casts[ply]
	local now = CurTime()
	if not rec then camState.shadow = nil return end
	local el = now - (rec.localStart or now)
	local F = Angle(0, rec.lockYaw or 0, 0):Forward()
	local Rt = F:Cross(Vector(0, 0, 1))
	local base = ply:GetPos()

	-- plan de 3/4 face pendant le sceau, pour voir le genou a terre
	if rec.phase == NARA.PH_WINDUP then
		local cinePos = base + F * 78 + Rt * 52 + Vector(0, 0, 38)
		local cineAng = (base + Vector(0, 0, 30) - cinePos):Angle()
		local k = ease(el / 0.35)
		camState.last = { pos = LerpVector(k, origin, cinePos), ang = LerpAngle(k, angles, cineAng), fov = Lerp(k, fov, 70) }
		camState.leave = nil
		return { origin = camState.last.pos, angles = camState.last.ang, fov = camState.last.fov, drawviewer = true }
	end

	if rec.phase == NARA.PH_STEER then
		local pos = TipCamera(rec, ply)
		local ang = Angle(math.Clamp(angles.p, C.CamPitchMin, C.CamPitchMax), angles.y, 0)
		-- leger roulis quand l'ombre tourne
		local yawSpeed = math.AngleDifference(angles.y, camState.prevYaw or angles.y) / math.max(FrameTime(), 0.001)
		camState.prevYaw = angles.y
		camState.roll = Lerp(math.min(1, FrameTime() * 6), camState.roll or 0, math.Clamp(-yawSpeed * 0.02, -6, 6))
		ang.r = camState.roll
		local fovT = C.CamFOV
		-- plongee de la camera vers la pointe, en arc
		local k = ease(el / C.CamDiveTime)
		if k < 1 and camState.last then
			local mid = LerpVector(0.5, camState.last.pos, pos) + Vector(0, 0, 40)
			pos = LerpVector(k, LerpVector(k, camState.last.pos, mid), LerpVector(k, mid, pos))
			ang = LerpAngle(k, camState.last.ang, ang)
			fovT = Lerp(k, camState.last.fov, fovT)
		end
		camState.shadow = { pos = pos, ang = ang, fov = fovT }
		camState.leave = nil
		return { origin = pos, angles = ang, fov = fovT, drawviewer = true }
	end

	-- retour de la camera dans le corps
	if camState.shadow then
		camState.leave = camState.leave or now
		local k = ease((now - camState.leave) / 0.5)
		if k >= 1 then
			camState.shadow, camState.leave = nil, nil
			return
		end
		return { origin = LerpVector(k, camState.shadow.pos, origin), angles = LerpAngle(k, camState.shadow.ang, angles),
			fov = Lerp(k, camState.shadow.fov, fov), drawviewer = k < 0.85 }
	end
end)

local function InShadowView()
	local rec = Casts[LocalPlayer()]
	return rec and (rec.phase == NARA.PH_WINDUP or rec.phase == NARA.PH_STEER) or camState.shadow ~= nil
end

hook.Add("PreDrawViewModel", "NaraKage_HideVM", function(vm, ply)
	if IsValid(ply) and ply == LocalPlayer() and InShadowView() then return true end
end)

hook.Add("HUDShouldDraw", "NaraKage_HideHUD", function(name)
	if name == "CHudCrosshair" and InShadowView() then return false end
end)

hook.Add("CreateMove", "NaraKage_Input", function(cmd)
	local ply = LocalPlayer()
	local rec = Casts[ply]
	if rec and rec.phase == NARA.PH_STEER then
		local a = cmd:GetViewAngles()
		local p = math.Clamp(a.p, C.CamPitchMin, C.CamPitchMax)
		if p ~= a.p then
			a.p = p
			cmd:SetViewAngles(a)
		end
	end
	-- cible prise : sa tete tourne comme celle du lanceur
	if IsValid(ply:GetNW2Entity("NaraBy")) then
		local a = cmd:GetViewAngles()
		a.y = ply:GetNW2Float("NaraMY")
		cmd:SetViewAngles(a)
	end
end)

-- ---------------------------------------------------------------- ecran : image sombre + vignettage doux

local function ShadowViewAmount()
	local rec = Casts[LocalPlayer()]
	local now = CurTime()
	if rec and rec.phase == NARA.PH_STEER then return ease((now - rec.localStart) / C.CamDiveTime) end
	if camState.shadow and camState.leave then return 1 - ease((now - camState.leave) / 0.5) end
	return 0
end

hook.Add("RenderScreenspaceEffects", "NaraKage_Screen", function()
	if not C.ScreenFX then return end
	local k = ShadowViewAmount()
	if IsValid(LocalPlayer():GetNW2Entity("NaraBy")) then k = math.max(k, 0.6) end
	if k <= 0.01 then return end
	DrawColorModify({
		["$pp_colour_addr"] = 0, ["$pp_colour_addg"] = 0, ["$pp_colour_addb"] = 0.01 * k,
		["$pp_colour_brightness"] = -0.07 * k, ["$pp_colour_contrast"] = 1 + 0.12 * k,
		["$pp_colour_colour"] = 1 - 0.18 * k,
		["$pp_colour_mulr"] = 0, ["$pp_colour_mulg"] = 0, ["$pp_colour_mulb"] = 0,
	})
	cam.Start2D()
	surface.SetMaterial(VIGNETTE)
	surface.SetDrawColor(0, 0, 0, 245 * k)
	surface.DrawTexturedRect(0, 0, ScrW(), ScrH())
	cam.End2D()
end)

-- ---------------------------------------------------------------- compteur (en bas au milieu)

local function Countdown(total, left, title, appear, hint)
	local sw, sh = ScrW(), ScrH()
	local cx, cy = sw / 2, sh - sh * 0.11
	local a = 255 * appear
	local frac = math.Clamp(left / total, 0, 1)
	local urgent = left <= 3

	-- fond : ovale noir doux
	surface.SetMaterial(POOL)
	surface.SetDrawColor(0, 0, 0, 120 * appear)
	surface.DrawTexturedRect(cx - sh * 0.30, cy - sh * 0.10, sh * 0.60, sh * 0.20)
	surface.SetDrawColor(0, 0, 0, 110 * appear)
	surface.DrawTexturedRect(cx - sh * 0.22, cy - sh * 0.075, sh * 0.44, sh * 0.15)

	-- chiffre : rebondit a chaque seconde
	local sub = left - math.floor(left)
	local pop = 1 + 0.18 * math.max(0, sub - 0.82) / 0.18
	local col = urgent and Color(255, 80, 60, a) or Color(245, 242, 235, a)
	local ny = cy - sh * 0.012
	local m = Matrix()
	m:Translate(Vector(cx, ny, 0))
	m:Scale(Vector(pop, pop, 1))
	m:Translate(Vector(-cx, -ny, 0))
	cam.PushModelMatrix(m)
	draw.SimpleText(tostring(math.max(0, math.ceil(left))), "NaraKage_Count", cx, ny, col, TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER)
	cam.PopModelMatrix()

	local bw, bh = sh * 0.26, math.max(3, sh * 0.005)
	local by = cy + sh * 0.036
	surface.SetDrawColor(255, 255, 255, 40 * appear)
	surface.DrawRect(cx - bw / 2, by, bw, bh)
	surface.SetDrawColor(col.r, col.g, col.b, a)
	surface.DrawRect(cx - bw / 2, by, bw * frac, bh)

	draw.SimpleText(title, "NaraKage_Label", cx, cy - sh * 0.06, Color(205, 200, 190, a * 0.9), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER)
	if hint then
		draw.SimpleText(hint, "NaraKage_Hint", cx, by + sh * 0.03, Color(195, 190, 180, a * 0.75), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER)
	end
end

local lastTick
hook.Add("HUDPaint", "NaraKage_HUD", function()
	local ply = LocalPlayer()
	local now = CurTime()
	local rec = Casts[ply]
	if rec and rec.phase == NARA.PH_STEER then
		local left = C.SteerTime - (now - rec.phaseStart)
		Countdown(C.SteerTime, left, "KAGEMANE NO JUTSU", ease((now - rec.localStart - C.CamDiveTime * 0.6) / 0.3),
			"Souris : diriger l'ombre    Avancer : accelerer    Reculer : ralentir    Clic droit : annuler")
		local s = math.ceil(left)
		if s <= 5 and s > 0 and s ~= lastTick then
			lastTick = s
			local snd = C.Sounds.Tick
			if snd and snd ~= "" then surface.PlaySound(snd) end
		end
		return
	end
	lastTick = nil
	if rec and rec.phase == NARA.PH_BOUND then
		Countdown(C.PossessTime, C.PossessTime - (now - rec.phaseStart), "KAGEMANE  ·  POSSESSION REUSSIE",
			ease((now - rec.localStart) / 0.3), "Ta cible imite tes mouvements    Clic droit : relacher")
		return
	end
	local by = ply:GetNW2Entity("NaraBy")
	local brec = IsValid(by) and Casts[by]
	if brec and brec.phase == NARA.PH_BOUND then
		Countdown(C.PossessTime, C.PossessTime - (now - brec.phaseStart), "PRIS DANS L'OMBRE", 1,
			"Tu imites les mouvements de ton adversaire")
	end
end)
