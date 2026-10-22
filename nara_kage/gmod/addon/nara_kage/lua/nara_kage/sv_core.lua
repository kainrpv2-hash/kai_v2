-- Nara : Kagemane no Jutsu - logique serveur

util.AddNetworkString("nara_kage_state")
util.AddNetworkString("nara_kage_pts")

local C = NARA.Config
local Casts = NARA.Casts

local function Snd(ent, key, lvl, pitch)
	local s = C.Sounds[key]
	if s and s ~= "" and IsValid(ent) then ent:EmitSound(s, lvl or 75, pitch or 100) end
end

local function WriteState(ply, rec, reset)
	net.Start("nara_kage_state")
	net.WriteEntity(ply)
	net.WriteUInt(rec.phase, 3)
	net.WriteFloat(rec.phaseStart)
	net.WriteEntity(IsValid(rec.target) and rec.target or NULL)
	net.WriteFloat(rec.lockYaw or 0)
	net.WriteBool(reset or false)
end

local function SendState(ply, rec, reset)
	WriteState(ply, rec, reset)
	net.Broadcast()
end

local function WritePoints(ply, rec, first, last)
	net.Start("nara_kage_pts")
	net.WriteEntity(ply)
	net.WriteUInt(first, 12)
	net.WriteUInt(last - first + 1, 7)
	for i = first, last do net.WriteVector(rec.path[i]) end
end

-- Envoie les nouveaux points de l'ombre (par paquets)
local function FlushPoints(ply, rec)
	while rec.sent < #rec.path do
		local first = rec.sent + 1
		local last = math.min(#rec.path, first + 63)
		WritePoints(ply, rec, first, last)
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

local function BindTarget(ply, rec, target)
	rec.target = target
	target.NaraBoundBy = ply
	target:SetNW2Entity("NaraBy", ply)
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
	if not IsValid(t) or t.NaraBoundBy == nil then return end
	t.NaraBoundBy = nil
	t:SetNW2Entity("NaraBy", NULL)
	if t:IsNPC() then t:ClearSchedule() end
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

local function Finish(ply, rec)
	StopCrawl(rec)
	FreeTarget(rec)
	rec.phase = NARA.PH_NONE
	rec.phaseStart = CurTime()
	SendState(ply, rec)
	Casts[ply] = nil
	if IsValid(ply) then ply.NaraNext = CurTime() + C.Cooldown end
end

function NARA.Cancel(ply)
	local rec = Casts[ply]
	if not rec then return end
	if rec.phase == NARA.PH_WINDUP then
		-- rien n'est encore parti : on arrete tout de suite
		rec.phase = NARA.PH_NONE
		rec.phaseStart = CurTime()
		SendState(ply, rec)
		Casts[ply] = nil
		return
	end
	Retract(ply, rec)
end

function NARA.Start(ply)
	if not IsValid(ply) or not ply:Alive() or Casts[ply] then return end
	if (ply.NaraNext or 0) > CurTime() or not ply:IsOnGround() then return end

	local feet = NARA.Ground(ply:GetPos(), 10, 40) or ply:GetPos()
	local yaw = ply:EyeAngles().y
	local rec = { phase = NARA.PH_NONE, phaseStart = CurTime(), path = { feet }, sent = 0,
		lockYaw = yaw, tipYaw = yaw, tip = feet, length = 0 }
	Casts[ply] = rec
	SetPhase(ply, rec, NARA.PH_WINDUP, true)
	FlushPoints(ply, rec)
	timer.Simple(0.32, function() if Casts[ply] == rec then Snd(ply, "Mudra", 72) end end)
end

-- ---------------------------------------------------------------- deplacement de la pointe

local function IgnoreLiving(e) return not (e:IsPlayer() or e:IsNPC() or e:IsNextBot()) end
local HULL_MIN, HULL_MAX = Vector(-3, -3, 0), Vector(3, 3, 4)

local function MoveTip(rec, dir, step)
	local tip = rec.tip
	local up = Vector(0, 0, 10)
	local want = tip + dir * step
	-- mur : l'ombre glisse le long
	local wall = util.TraceHull({ start = tip + up, endpos = want + up, mins = HULL_MIN, maxs = HULL_MAX,
		mask = MASK_SOLID, filter = IgnoreLiving })
	if wall.Hit and wall.HitNormal.z < 0.55 then
		local n = Vector(wall.HitNormal.x, wall.HitNormal.y, 0)
		n:Normalize()
		local slide = dir - n * dir:Dot(n)
		if slide:Length() < 0.2 then return false end
		want = tip + slide * step
		local again = util.TraceHull({ start = tip + up, endpos = want + up, mins = HULL_MIN, maxs = HULL_MAX,
			mask = MASK_SOLID, filter = IgnoreLiving })
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

local function TargetAlive(t)
	if not IsValid(t) then return false end
	if t:IsPlayer() then return t:Alive() end
	return t:Health() > 0 or t:IsNextBot()
end

-- ---------------------------------------------------------------- boucle

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
		if rec.length < C.MaxLength then
			local before = rec.tip
			if MoveTip(rec, Angle(0, rec.tipYaw, 0):Forward(), speed * dt) then
				rec.length = rec.length + rec.tip:Distance(before)
			end
		end
		if rec.tip:Distance(rec.path[#rec.path]) >= 7 then rec.path[#rec.path + 1] = rec.tip end
		if rec.crawl then rec.crawl:ChangePitch(rec.keyFwd and 118 or 100, 0.2) end

		local hit = TryCatch(ply, rec)
		if hit then
			if rec.tip:Distance(rec.path[#rec.path]) > 0.5 then rec.path[#rec.path + 1] = rec.tip end
			FlushPoints(ply, rec)
			StopCrawl(rec)
			BindTarget(ply, rec, hit)
			SetPhase(ply, rec, NARA.PH_BOUND)
			Snd(hit, "Bind", 82)
			return
		end
		if el >= C.SteerTime then Retract(ply, rec) end

	elseif rec.phase == NARA.PH_BOUND then
		local t = rec.target
		if not TargetAlive(t) or ply:GetPos():Distance(t:GetPos()) > C.BreakDistance or el >= C.PossessTime then
			return Retract(ply, rec)
		end
		if rec.pin and not t:IsPlayer() then
			if t:GetPos():DistToSqr(rec.pin) > 1 then t:SetPos(rec.pin) end
			if t:IsNPC() and t:GetCurrentSchedule() ~= SCHED_NPC_FREEZE then t:SetSchedule(SCHED_NPC_FREEZE) end
		end

	elseif rec.phase == NARA.PH_RETRACT then
		if now >= (rec.retractEnd or 0) then return Finish(ply, rec) end
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

hook.Add("PlayerDisconnected", "NaraKage_Leave", function(ply)
	local rec = Casts[ply]
	if not rec then return end
	StopCrawl(rec)
	FreeTarget(rec)
	Casts[ply] = nil
	rec.phase = NARA.PH_NONE
	rec.phaseStart = CurTime()
	SendState(ply, rec)
end)

-- Un joueur qui arrive en cours de technique recoit l'etat et le trace de l'ombre
hook.Add("PlayerInitialSpawn", "NaraKage_Sync", function(newcomer)
	timer.Simple(3, function()
		if not IsValid(newcomer) then return end
		for ply, rec in pairs(Casts) do
			if IsValid(ply) then
				WriteState(ply, rec, true)
				net.Send(newcomer)
				for first = 1, #rec.path, 64 do
					WritePoints(ply, rec, first, math.min(#rec.path, first + 63))
					net.Send(newcomer)
				end
			end
		end
	end)
end)
