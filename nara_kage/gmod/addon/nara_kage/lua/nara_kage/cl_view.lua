-- Nara : manipulation des ombres - camera dans la pointe de l'ombre, compteur, effets d'ecran

NARA = NARA or {}
local C = NARA.Config
local Casts = NARA.Casts

local function ease(x) x = math.Clamp(x, 0, 1) return x * x * (3 - 2 * x) end

surface.CreateFont("NaraKage_Count", { font = "Roboto", size = ScreenScale(30), weight = 800, antialias = true })
surface.CreateFont("NaraKage_Dec", { font = "Roboto", size = ScreenScale(13), weight = 700, antialias = true })
surface.CreateFont("NaraKage_Label", { font = "Roboto", size = ScreenScale(7), weight = 600, antialias = true })
surface.CreateFont("NaraKage_Hint", { font = "Roboto", size = ScreenScale(5.5), weight = 500, antialias = true })

local VIGNETTE = Material("nara_kage/shadow_vignette")

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
	if not rec then return end
	if NARA.CasterFrozen(rec) or (rec.wKneel or 0) > 0.01 then
		-- le corps reste tourne vers la ou l'ombre est partie, meme si la camera tourne
		ply:SetRenderAngles(Angle(0, rec.lockYaw or ply:GetRenderAngles().y, 0))
		ply:SetPoseParameter("aim_yaw", 0)
		ply:SetPoseParameter("aim_pitch", 0)
		ply:SetPoseParameter("head_yaw", 0)
		ply:SetPoseParameter("head_pitch", 0)
		ply:SetPoseParameter("move_x", 0)
		ply:SetPoseParameter("move_y", 0)
		ply:InvalidateBoneCache()
	end
end)

-- ---------------------------------------------------------------- camera

local camState = { blend = 0 }

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
	if not rec then camState.blend = 0 return end
	local tech, phase = rec.tech, rec.phase
	if tech ~= 1 then return end
	local el = now - (rec.localStart or now)
	local F = Angle(0, rec.lockYaw or 0, 0):Forward()
	local Rt = F:Cross(Vector(0, 0, 1))
	local base = ply:GetPos()

	-- plan cinematique de 3/4 face pendant le sceau
	local cineAng = function(pos) return (base + Vector(0, 0, 30) - pos):Angle() end
	local cinePos = base + F * 78 + Rt * 52 + Vector(0, 0, 38)

	if phase == NARA.PH_WINDUP then
		local k = ease(el / 0.35)
		camState.last = { pos = LerpVector(k, origin, cinePos), ang = LerpAngle(k, angles, cineAng(cinePos)), fov = Lerp(k, fov, 70) }
		camState.leave = nil
		return { origin = camState.last.pos, angles = camState.last.ang, fov = camState.last.fov, drawviewer = true }
	end

	if phase == NARA.PH_STEER then
		local tipPos = TipCamera(rec, ply)
		local ang = Angle(math.Clamp(angles.p, C.CamPitchMin, C.CamPitchMax), angles.y, 0)
		-- leger roulis quand l'ombre tourne
		local yawSpeed = math.AngleDifference(angles.y, camState.prevYaw or angles.y) / math.max(FrameTime(), 0.001)
		camState.prevYaw = angles.y
		camState.roll = Lerp(math.min(1, FrameTime() * 6), camState.roll or 0, math.Clamp(-yawSpeed * 0.02, -7, 7))
		ang.r = camState.roll + math.sin(RealTime() * 2.1) * 0.6
		local pos = tipPos + Vector(0, 0, math.sin(RealTime() * 7) * 0.4)
		local fovT = C.CamFOV
		-- plongee de la camera vers la pointe
		local k = ease(el / C.CamDiveTime)
		if k < 1 and camState.last then
			local mid = LerpVector(0.5, camState.last.pos, pos) + Vector(0, 0, 40)
			local a = LerpVector(k, camState.last.pos, mid)
			local b = LerpVector(k, mid, pos)
			pos = LerpVector(k, a, b)
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

hook.Add("PreDrawViewModel", "NaraKage_HideVM", function(vm, ply)
	local rec = IsValid(ply) and Casts[ply]
	if rec and rec.tech == 1 and (rec.phase == NARA.PH_WINDUP or rec.phase == NARA.PH_STEER or camState.shadow) then return true end
end)

hook.Add("CreateMove", "NaraKage_Input", function(cmd)
	local ply = LocalPlayer()
	local rec = Casts[ply]
	if rec and rec.tech == 1 and rec.phase == NARA.PH_STEER then
		local a = cmd:GetViewAngles()
		local p = math.Clamp(a.p, C.CamPitchMin, C.CamPitchMax)
		if p ~= a.p then
			a.p = p
			cmd:SetViewAngles(a)
		end
	end
	-- cible prise par Kagemane : sa tete tourne comme celle du lanceur
	if IsValid(ply:GetNW2Entity("NaraBy")) and ply:GetNW2Int("NaraMode") == 1 then
		local a = cmd:GetViewAngles()
		a.y = ply:GetNW2Float("NaraMY")
		cmd:SetViewAngles(a)
	end
end)

hook.Add("HUDShouldDraw", "NaraKage_HideHUD", function(name)
	if name ~= "CHudCrosshair" then return end
	local rec = Casts[LocalPlayer()]
	if rec and rec.tech == 1 and (rec.phase == NARA.PH_WINDUP or rec.phase == NARA.PH_STEER) then return false end
end)

-- ---------------------------------------------------------------- ecran

local function ShadowViewAmount()
	local rec = Casts[LocalPlayer()]
	if not rec or rec.tech ~= 1 then return 0 end
	local now = CurTime()
	if rec.phase == NARA.PH_STEER then return ease((now - rec.localStart) / C.CamDiveTime) end
	if camState.shadow and camState.leave then return 1 - ease((now - camState.leave) / 0.5) end
	return 0
end

hook.Add("RenderScreenspaceEffects", "NaraKage_Screen", function()
	if not C.ScreenFX then return end
	local k = ShadowViewAmount()
	local ply = LocalPlayer()
	if IsValid(ply:GetNW2Entity("NaraBy")) then k = math.max(k, 0.55) end
	if k <= 0.01 then return end
	DrawColorModify({
		["$pp_colour_addr"] = 0, ["$pp_colour_addg"] = 0, ["$pp_colour_addb"] = 0.012 * k,
		["$pp_colour_brightness"] = -0.05 * k, ["$pp_colour_contrast"] = 1 + 0.18 * k,
		["$pp_colour_colour"] = 1 - 0.62 * k,
		["$pp_colour_mulr"] = 0, ["$pp_colour_mulg"] = 0, ["$pp_colour_mulb"] = 0,
	})
	cam.Start2D()
	surface.SetMaterial(VIGNETTE)
	surface.SetDrawColor(0, 0, 0, 235 * k)
	local pulse = 1 + 0.015 * math.sin(RealTime() * 2.4)
	local w, h = ScrW() * pulse, ScrH() * pulse
	surface.DrawTexturedRect((ScrW() - w) / 2, (ScrH() - h) / 2, w, h)
	cam.End2D()
end)

-- ---------------------------------------------------------------- compteur

local RIBBON = Material("nara_kage/shadow_ribbon")

local function InkPanel(cx, cy, w, h, a)
	surface.SetMaterial(RIBBON)
	surface.SetDrawColor(0, 0, 0, a)
	surface.DrawTexturedRectUV(cx - w / 2, cy - h / 2, w, h, 0.1, 0, 0.75, 1)
	surface.SetDrawColor(0, 0, 0, a * 0.5)
	surface.DrawTexturedRectUV(cx - w * 0.6, cy - h * 0.62, w * 1.2, h * 1.24, 0.4, 0, 1.0, 1)
end

local function Countdown(total, left, title, appear, hint)
	local sw, sh = ScrW(), ScrH()
	local cx, cy = sw / 2, sh - sh * 0.11
	local a = 255 * appear
	local urgent = left <= 3
	local secs = math.max(0, math.ceil(left))
	local frac = math.Clamp(left / total, 0, 1)

	InkPanel(cx, cy, sh * 0.46, sh * 0.15, 215 * appear)

	-- chiffre principal : rebondit a chaque seconde
	local sub = left - math.floor(left)
	local pop = 1 + 0.18 * math.max(0, sub - 0.82) / 0.18
	local col = urgent and Color(255, 70 + 120 * sub, 60, a) or Color(245, 240, 230, a)
	local m = Matrix()
	m:Translate(Vector(cx, cy - sh * 0.012, 0))
	m:Scale(Vector(pop, pop, 1))
	m:Translate(Vector(-cx, -(cy - sh * 0.012), 0))
	cam.PushModelMatrix(m)
	draw.SimpleText(tostring(secs), "NaraKage_Count", cx, cy - sh * 0.012, col, TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER)
	cam.PopModelMatrix()

	-- barre de chakra qui se vide
	local bw, bh = sh * 0.30, math.max(3, sh * 0.006)
	local by = cy + sh * 0.038
	surface.SetDrawColor(255, 255, 255, 40 * appear)
	surface.DrawRect(cx - bw / 2, by, bw, bh)
	surface.SetDrawColor(col.r, col.g, col.b, a)
	surface.DrawRect(cx - bw / 2, by, bw * frac, bh)

	draw.SimpleText(title, "NaraKage_Label", cx, cy - sh * 0.062, Color(200, 195, 185, a * 0.9), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER)
	if hint then
		draw.SimpleText(hint, "NaraKage_Hint", cx, by + sh * 0.025, Color(190, 185, 175, a * 0.75), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER)
	end
end

local lastTick
hook.Add("HUDPaint", "NaraKage_HUD", function()
	local ply = LocalPlayer()
	local now = CurTime()
	local rec = Casts[ply]
	if rec and rec.tech == 1 and rec.phase == NARA.PH_STEER then
		local left = C.SteerTime - (now - rec.phaseStart)
		local appear = ease((now - rec.localStart - C.CamDiveTime * 0.6) / 0.3)
		Countdown(C.SteerTime, left, "KAGEMANE NO JUTSU  ·  MANIPULATION DES OMBRES", appear,
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
		local left = C.PossessTime - (now - rec.phaseStart)
		Countdown(C.PossessTime, left, "KAGEMANE  ·  POSSESSION REUSSIE", ease((now - rec.localStart) / 0.3),
			"Ta cible imite tes mouvements    R + clic gauche : enchainer    Clic droit : relacher")
		return
	end
	local by = ply:GetNW2Entity("NaraBy")
	if IsValid(by) then
		local brec = Casts[by]
		local title = "PRIS DANS L'OMBRE"
		local total, left = 1, 1
		if brec and brec.phase == NARA.PH_BOUND then
			total, left = C.PossessTime, C.PossessTime - (now - brec.phaseStart)
		elseif brec and brec.phase == NARA.PH_CHOKE then
			title, total = "ETREINTE DE L'OMBRE", C.ChokeClimbTime + C.ChokeTime
			left = total - (now - brec.phaseStart)
		elseif brec and brec.phase == NARA.PH_PIERCE then
			title, total = "COUSU PAR LES OMBRES", C.NuiHoldTime
			left = total - (now - brec.phaseStart)
		end
		Countdown(total, left, title, 1, "Tu ne controles plus ton corps")
	end
end)
