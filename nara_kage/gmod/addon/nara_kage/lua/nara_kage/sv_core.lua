-- Nara : manipulation des ombres - logique serveur

util.AddNetworkString("nara_kage_state")
util.AddNetworkString("nara_kage_pts")

local C = NARA.Config
local Casts = NARA.Casts

local function Snd(ent, key, lvl, pitch)
	local s = C.Sounds[key]
	if s and s ~= "" and IsValid(ent) then ent:EmitSound(s, lvl or 75, pitch or 100) end
end

local function SendState(ply, rec, reset)
	net.Start("nara_kage_state")
	net.WriteEntity(ply)
	net.WriteUInt(rec.phase, 4)
	net.WriteUInt(rec.tech, 3)
	net.WriteFloat(rec.phaseStart)
	net.WriteEntity(IsValid(rec.target) and rec.target or NULL)
	net.WriteFloat(rec.lockYaw or 0)
	net.WriteBool(reset or false)
	net.Broadcast()
end

-- Envoie les nouveaux points de l'ombre (par paquets)
local function FlushPoints(ply, rec)
	local n = #rec.path
	while rec.sent < n do
		local first = rec.sent + 1
		local last = math.min(n, first + 63)
		net.Start("nara_kage_pts")
		net.WriteEntity(ply)
		net.WriteUInt(first, 12)
		net.WriteUInt(last - first + 1, 7)
		for i = first, last do net.WriteVector(rec.path[i]) end
		net.Broadcast()
		rec.sent = last
	end
end

local function SetPhase(ply, rec, phase, reset)
	rec.phase = phase
	rec.phaseStart = CurTime()
	SendState(ply, rec, reset)
end

local function StopCrawl(rec)
	if rec.crawl then
		rec.crawl:FadeOut(0.3)
		rec.crawl = nil
	end
end

-- ---------------------------------------------------------------- cible

local function BindTarget(ply, rec, target, mode)
	rec.target = target
	target.NaraBoundBy = ply
	target:SetNW2Entity("NaraBy", ply)
	target:SetNW2Int("NaraMode", mode)
	if target:IsPlayer() then
		rec.targetYaw = target:EyeAngles().y
		rec.casterYaw = ply:EyeAngles().y
		target:SetNW2Float("NaraMF", 0)
		target:SetNW2Float("NaraMS", 0)
		target:SetNW2Int("NaraMB", 0)
		target:SetNW2Float("NaraMY", rec.targetYaw)
	else
		rec.pin = target:GetPos()
		if target:IsNPC() then
			target:StopMoving()
			target:SetSchedule(SCHED_NPC_FREEZE)
		end
	end
end

local function FreeTarget(rec)
	local t = rec.target
	if not IsValid(t) then return end
	if t.NaraBoundBy ~= nil then
		t.NaraBoundBy = nil
		t:SetNW2Entity("NaraBy", NULL)
		t:SetNW2Int("NaraMode", 0)
		if t:IsNPC() then t:ClearSchedule() end
	end
end

local function Retract(ply, rec)
	if rec.phase == NARA.PH_RETRACT then return end
	StopCrawl(rec)
	FreeTarget(rec)
	-- longueur a ravaler : chemin parcouru, ou lien direct si une cible etait prise
	local len = NARA.PathLength(rec.path)
	if IsValid(rec.target) then len = math.max(len, ply:GetPos():Distance(rec.target:GetPos())) end
	rec.retractEnd = CurTime() + len / C.RetractSpeed + 0.25
	SetPhase(ply, rec, NARA.PH_RETRACT)
	Snd(ply, "Release", 70)
end

function NARA.Cancel(ply)
	local rec = Casts[ply]
	if not rec then return end
	if rec.phase == NARA.PH_WINDUP then
		-- rien n'est encore parti : on arrete tout de suite
		StopCrawl(rec)
		rec.phase = NARA.PH_NONE
		rec.phaseStart = CurTime()
		SendState(ply, rec)
		Casts[ply] = nil
		return
	end
	Retract(ply, rec)
end

local function Finish(ply, rec)
	StopCrawl(rec)
	FreeTarget(rec)
	rec.phase = NARA.PH_NONE
	rec.phaseStart = CurTime()
	SendState(ply, rec)
	Casts[ply] = nil
	if IsValid(ply) then ply.NaraNext = CurTime() + C.Cooldown end
end

-- ---------------------------------------------------------------- lancement

-- Cible visee (tolerant : un petit cone autour du viseur)
local function AimTarget(ply, range)
	local tr = ply:GetEyeTrace()
	if NARA.IsTarget(tr.Entity, ply) and tr.HitPos:Distance(ply:EyePos()) <= range then return tr.Entity end
	local eye, aim = ply:EyePos(), ply:GetAimVector()
	local best, bestDot
	for _, e in ipairs(ents.FindInSphere(eye, range)) do
		if NARA.IsTarget(e, ply) then
			local to = e:WorldSpaceCenter() - eye
			local dot = aim:Dot(to:GetNormalized())
			if dot > 0.985 and (not bestDot or dot > bestDot) then
				local vis = util.TraceLine({ start = eye, endpos = e:WorldSpaceCenter(), filter = { ply, e }, mask = MASK_SHOT })
				if not vis.Hit then best, bestDot = e, dot end
			end
		end
	end
	return best
end

function NARA.Start(ply, tech)
	if not IsValid(ply) or not ply:Alive() then return end
	local rec = Casts[ply]

	-- enchainement : une cible deja prise par Kagemane recoit directement la technique
	if rec then
		if rec.phase == NARA.PH_BOUND and tech ~= 1 and IsValid(rec.target) then
			rec.tech = tech
			rec.lockYaw = ply:EyeAngles().y
			rec.target:SetNW2Int("NaraMode", 2)
			rec.dmgNext = nil
			rec.pierced = nil
			SetPhase(ply, rec, tech == 2 and NARA.PH_CHOKE or NARA.PH_PIERCE)
			Snd(rec.target, tech == 2 and "Choke" or "Pierce", 80)
			Snd(ply, "Mudra", 70)
		end
		return
	end
	if (ply.NaraNext or 0) > CurTime() then return end
	if not ply:IsOnGround() then return end

	local feet = NARA.Ground(ply:GetPos(), 10, 40) or ply:GetPos()
	rec = { tech = tech, phase = NARA.PH_NONE, phaseStart = CurTime(), path = { feet }, sent = 0,
		lockYaw = ply:EyeAngles().y }

	if tech == 1 then
		Casts[ply] = rec
		rec.tipYaw = rec.lockYaw
		rec.tip = feet
		SetPhase(ply, rec, NARA.PH_WINDUP, true)
		FlushPoints(ply, rec)
		timer.Simple(0.32, function() if Casts[ply] == rec then Snd(ply, "Mudra", 72) end end)
		return
	end

	local range = tech == 2 and C.ChokeRange or C.NuiRange
	local target = AimTarget(ply, range)
	if not target or IsValid(target:GetNW2Entity("NaraBy")) then
		ply:ChatPrint("[Nara] Aucune cible a portee de ton ombre.")
		return
	end
	Casts[ply] = rec
	rec.target = target
	rec.route = NARA.GroundLine(feet, NARA.Ground(target:GetPos(), 20, 60) or target:GetPos(), 10)
	rec.routeLen = NARA.PathLength(rec.route)
	rec.travel = 0
	rec.lockYaw = (target:GetPos() - ply:GetPos()):Angle().y
	SetPhase(ply, rec, NARA.PH_TRAVEL, true)
	FlushPoints(ply, rec)
	Snd(ply, "Mudra", 72)
	Snd(ply, "Cast", 75, 115)
end

-- ---------------------------------------------------------------- deplacement de la pointe

local function MoveTip(rec, dir, step)
	local tip = rec.tip
	local up = Vector(0, 0, 10)
	local want = tip + dir * step
	-- mur : l'ombre glisse le long
	local wall = util.TraceHull({ start = tip + up, endpos = want + up, mins = Vector(-3, -3, 0), maxs = Vector(3, 3, 4),
		mask = MASK_SOLID, filter = function(e) return not (e:IsPlayer() or e:IsNPC() or e:IsNextBot()) end })
	if wall.Hit and wall.HitNormal.z < 0.55 then
		local n = Vector(wall.HitNormal.x, wall.HitNormal.y, 0)
		n:Normalize()
		local slide = dir - n * dir:Dot(n)
		if slide:Length() < 0.2 then return false end
		want = tip + slide * step * slide:Length()
		local again = util.TraceHull({ start = tip + up, endpos = want + up, mins = Vector(-3, -3, 0), maxs = Vector(3, 3, 4),
			mask = MASK_SOLID, filter = function(e) return not (e:IsPlayer() or e:IsNPC() or e:IsNextBot()) end })
		if again.Hit and again.HitNormal.z < 0.55 then return false end
	end
	local g = NARA.Ground(want, 26, 60)
	if not g or math.abs(g.z - tip.z) > 26 then return false end   -- vide ou marche trop haute
	rec.tip = g
	return true
end

local function TryCatch(ply, rec)
	for _, e in ipairs(ents.FindInSphere(rec.tip, C.CatchRadius + 48)) do
		if NARA.IsTarget(e, ply) and not IsValid(e:GetNW2Entity("NaraBy")) then
			local d = e:GetPos() - rec.tip
			local r = C.CatchRadius + math.min(24, e:BoundingRadius() * 0.3)
			if math.abs(d.z) < 50 and d:Length2D() <= r then return e end
		end
	end
end

-- ---------------------------------------------------------------- boucle

local function Damage(ply, target, amount, dtype, pos)
	local dmg = DamageInfo()
	dmg:SetDamage(amount * GetConVar("nara_kage_damage_scale"):GetFloat())
	dmg:SetAttacker(ply)
	local wep = ply:GetActiveWeapon()
	dmg:SetInflictor(IsValid(wep) and wep or ply)
	dmg:SetDamageType(dtype)
	dmg:SetDamagePosition(pos or target:WorldSpaceCenter())
	target:TakeDamageInfo(dmg)
end

local function TargetAlive(t)
	if not IsValid(t) then return false end
	if t:IsPlayer() then return t:Alive() end
	return t:Health() > 0 or t:IsNextBot()
end

local function ThinkCast(ply, rec)
	local now = CurTime()
	local dt = FrameTime()
	local el = now - rec.phaseStart

	if rec.phase == NARA.PH_WINDUP then
		if el >= C.WindupTime then
			SetPhase(ply, rec, NARA.PH_STEER)
			Snd(ply, "Cast", 78)
			local crawl = C.Sounds.Crawl
			if crawl and crawl ~= "" then
				rec.crawl = CreateSound(ply, crawl)
				rec.crawl:PlayEx(0.55, 100)
			end
		end

	elseif rec.phase == NARA.PH_STEER then
		-- l'ombre tourne vers la ou regarde la camera, avec une vitesse de virage limitee
		local diff = math.AngleDifference(ply:EyeAngles().y, rec.tipYaw)
		local maxTurn = C.TurnRate * dt
		rec.tipYaw = rec.tipYaw + math.Clamp(diff, -maxTurn, maxTurn)
		local speed = rec.keyFwd and C.BoostSpeed or (rec.keyBack and C.SlowSpeed or C.ShadowSpeed)
		rec.length = rec.length or 0
		if rec.length < C.MaxLength then
			local before = rec.tip
			if MoveTip(rec, Angle(0, rec.tipYaw, 0):Forward(), speed * dt) then
				rec.length = rec.length + rec.tip:Distance(before)
			end
		end
		local last = rec.path[#rec.path]
		if rec.tip:Distance(last) >= 7 then rec.path[#rec.path + 1] = rec.tip end
		if rec.crawl then rec.crawl:ChangePitch(rec.keyFwd and 118 or 100, 0.2) end

		local hit = TryCatch(ply, rec)
		if hit then
			if rec.tip:Distance(rec.path[#rec.path]) > 0.5 then rec.path[#rec.path + 1] = rec.tip end
			FlushPoints(ply, rec)
			StopCrawl(rec)
			BindTarget(ply, rec, hit, 1)
			SetPhase(ply, rec, NARA.PH_BOUND)
			Snd(hit, "Bind", 82)
			return
		end
		if el >= C.SteerTime then Retract(ply, rec) end

	elseif rec.phase == NARA.PH_TRAVEL then
		if not TargetAlive(rec.target) then return Retract(ply, rec) end
		rec.travel = math.min(rec.routeLen, rec.travel + C.TravelSpeed * dt)
		-- ajoute les points de la route deja parcourus
		local acc = NARA.PathLength(rec.path)
		local i = #rec.path
		while i < #rec.route do
			local seg = rec.route[i + 1]:Distance(rec.route[i])
			if acc + seg > rec.travel then break end
			acc = acc + seg
			i = i + 1
			rec.path[i] = rec.route[i]
		end
		if rec.travel >= rec.routeLen then
			BindTarget(ply, rec, rec.target, 2)
			if rec.tech == 2 then
				SetPhase(ply, rec, NARA.PH_CHOKE)
				Snd(rec.target, "Choke", 80)
			else
				SetPhase(ply, rec, NARA.PH_PIERCE)
				Snd(rec.target, "Pierce", 85)
			end
		end

	elseif rec.phase == NARA.PH_BOUND or rec.phase == NARA.PH_CHOKE or rec.phase == NARA.PH_PIERCE then
		local t = rec.target
		if not TargetAlive(t) or ply:GetPos():Distance(t:GetPos()) > C.BreakDistance then
			return Retract(ply, rec)
		end
		if rec.pin and not t:IsPlayer() then
			if t:GetPos():DistToSqr(rec.pin) > 1 then t:SetPos(rec.pin) end
			if t:IsNPC() and t:GetCurrentSchedule() ~= SCHED_NPC_FREEZE then t:SetSchedule(SCHED_NPC_FREEZE) end
		end
		if rec.phase == NARA.PH_BOUND then
			if el >= C.PossessTime then Retract(ply, rec) end
		elseif rec.phase == NARA.PH_CHOKE then
			if el >= C.ChokeClimbTime then
				rec.dmgNext = rec.dmgNext or now
				if now >= rec.dmgNext then
					rec.dmgNext = now + 0.25
					Damage(ply, t, C.ChokeDPS * 0.25, DMG_GENERIC, NARA.NeckPos(t))
					if t:IsPlayer() then util.ScreenShake(t:GetPos(), 3, 12, 0.3, 40) end
				end
			end
			if el >= C.ChokeClimbTime + C.ChokeTime then Retract(ply, rec) end
		else
			if not rec.pierced and el >= 0.17 then
				rec.pierced = true
				Damage(ply, t, C.NuiDamage, DMG_SLASH)
				if t:IsPlayer() then util.ScreenShake(t:GetPos(), 6, 20, 0.5, 40) end
			end
			if el >= C.NuiHoldTime + 0.2 then Retract(ply, rec) end
		end

	elseif rec.phase == NARA.PH_RETRACT then
		if now >= (rec.retractEnd or 0) then Finish(ply, rec) end
	end

	FlushPoints(ply, rec)
end

hook.Add("Think", "NaraKage_Think", function()
	for ply, rec in pairs(Casts) do
		if not IsValid(ply) then
			FreeTarget(rec)
			StopCrawl(rec)
			Casts[ply] = nil
		elseif not ply:Alive() then
			Finish(ply, rec)
		else
			ThinkCast(ply, rec)
		end
	end
end)

hook.Add("PlayerDeath", "NaraKage_Death", function(ply)
	if Casts[ply] then Finish(ply, Casts[ply]) end
end)

hook.Add("PlayerDisconnected", "NaraKage_Leave", function(ply)
	local rec = Casts[ply]
	if rec then
		StopCrawl(rec)
		FreeTarget(rec)
		Casts[ply] = nil
		rec.phase = NARA.PH_NONE
		rec.phaseStart = CurTime()
		SendState(ply, rec)
	end
end)

-- Un joueur qui arrive en cours de technique recoit l'etat et le trace de l'ombre
hook.Add("PlayerInitialSpawn", "NaraKage_Sync", function(newcomer)
	timer.Simple(3, function()
		if not IsValid(newcomer) then return end
		for ply, rec in pairs(Casts) do
			if IsValid(ply) then
				net.Start("nara_kage_state")
				net.WriteEntity(ply)
				net.WriteUInt(rec.phase, 4)
				net.WriteUInt(rec.tech, 3)
				net.WriteFloat(rec.phaseStart)
				net.WriteEntity(IsValid(rec.target) and rec.target or NULL)
				net.WriteFloat(rec.lockYaw or 0)
				net.WriteBool(true)
				net.Send(newcomer)
				for first = 1, #rec.path, 64 do
					local last = math.min(#rec.path, first + 63)
					net.Start("nara_kage_pts")
					net.WriteEntity(ply)
					net.WriteUInt(first, 12)
					net.WriteUInt(last - first + 1, 7)
					for i = first, last do net.WriteVector(rec.path[i]) end
					net.Send(newcomer)
				end
			end
		end
	end)
end)
