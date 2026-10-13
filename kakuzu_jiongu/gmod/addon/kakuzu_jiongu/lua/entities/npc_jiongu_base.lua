-- Base NextBot des quatre monstres masques de Kakuzu (Jiongu)
AddCSLuaFile()

ENT.Base = "base_nextbot"
ENT.Type = "nextbot"
ENT.PrintName = "Jiongu (base)"
ENT.Author = "Kakuzu Jiongu pack"
ENT.Category = "Naruto - Kakuzu (Jiongu)"
ENT.Spawnable = false
ENT.AdminOnly = false

-- Reglages surcharges par chaque monstre
ENT.JModel = "models/kakuzu_jiongu/jiongu_katon.mdl"
ENT.JElement = "katon"
ENT.JHealth = 900
ENT.JSpeed = 140          -- vitesse de marche (unites/s)
ENT.JRange = 1100         -- portee de la technique
ENT.JMinRange = 90        -- trop pres : coup de griffe a la place
ENT.JCooldown = 4         -- secondes entre deux techniques
ENT.JMaskHeight = 92      -- hauteur du masque (point de depart des techniques)
ENT.JHull = 42            -- demi-largeur de la boite de collision
ENT.JHullHeight = 120
ENT.JSightRange = 2000
ENT.JImpactDelay = 0.8    -- moment ou la technique part pendant l'animation d'attaque

local GROWLS = {
	"npc/antlion_guard/angry1.wav", "npc/antlion_guard/angry2.wav", "npc/antlion_guard/angry3.wav",
	"npc/zombie_poison/pz_alert1.wav", "npc/zombie_poison/pz_alert2.wav",
}

function ENT:SetupDataTables()
	self:NetworkVar("Entity", 0, "JOwnerPlayer")
end

-- Les cycles de marche sont "sur place" : on n'utilise pas BodyMoveXY (vitesse au sol nulle),
-- on regle la vitesse de lecture sur la vitesse reelle du NextBot.
function ENT:BodyUpdate()
	local act = self:GetActivity()
	if SERVER and (act == ACT_WALK or act == ACT_RUN) then
		local v = self.loco:GetVelocity():Length2D()
		self:SetPlaybackRate(math.Clamp(v / math.max(self.JSpeed, 1), 0.35, 1.8))
	end
	self:FrameAdvance()
end

function ENT:Initialize()
	self:SetModel(self.JModel)
	local scale = GetConVar("jiongu_model_scale") and GetConVar("jiongu_model_scale"):GetFloat() or 1
	if scale ~= 1 then self:SetModelScale(scale, 0) end
	if SERVER then
		self:SetHealth(self.JHealth)
		self:SetMaxHealth(self.JHealth)
		self:SetCollisionBounds(Vector(-self.JHull, -self.JHull, 0) * scale, Vector(self.JHull, self.JHull, self.JHullHeight) * scale)
		self.loco:SetStepHeight(28)
		self.loco:SetJumpHeight(70)
		self.loco:SetAcceleration(500)
		self.loco:SetDeceleration(900)
		self.loco:SetDesiredSpeed(self.JSpeed)
		self.NextJutsu = CurTime() + 1
		self.NextGrowl = CurTime() + math.Rand(4, 10)
		self:EmitSound(GROWLS[math.random(#GROWLS)], 85, 70)
	end
end

if SERVER then

	-- ------------------------------------------------------------ cibles
	function ENT:SetJionguEnemy(ent)
		if self:IsValidTarget(ent) then
			self.JEnemy = ent
			self.JEnemyForced = CurTime() + 20
		end
	end

	function ENT:IsFriend(ent)
		local owner = self.JOwner
		if ent == self then return true end
		if IsValid(owner) and ent == owner then return true end
		if ent.JElement ~= nil then
			-- deux monstres du meme maitre (ou deux monstres sauvages) ne se battent pas
			return ent.JOwner == owner
		end
		return false
	end

	function ENT:IsValidTarget(ent)
		if not IsValid(ent) or self:IsFriend(ent) then return false end
		if ent:IsPlayer() then
			return ent:Alive() and not ent:IsFlagSet(FL_NOTARGET) and ent:GetMoveType() ~= MOVETYPE_NOCLIP
		end
		if ent:IsNPC() or ent:IsNextBot() then
			return ent:Health() > 0
		end
		return false
	end

	function ENT:FindTarget()
		if IsValid(self.JEnemy) and self:IsValidTarget(self.JEnemy) then
			if (self.JEnemyForced or 0) > CurTime() or self:Visible(self.JEnemy) then
				return self.JEnemy
			end
		end
		self.JEnemy = nil
		local hostile = GetConVar("jiongu_hostile"):GetBool()
		local guard = IsValid(self.JOwner)
		local best, bestDist = nil, self.JSightRange * self.JSightRange
		for _, ent in ipairs(ents.FindInSphere(self:GetPos(), self.JSightRange)) do
			if self:IsValidTarget(ent) then
				-- un monstre invoque n'attaque personne de lui-meme : il protege son maitre
				local allowed = (not guard) and (hostile or not ent:IsPlayer())
				if allowed then
					local d = self:GetPos():DistToSqr(ent:GetPos())
					if d < bestDist and self:Visible(ent) then
						best, bestDist = ent, d
					end
				end
			end
		end
		self.JEnemy = best
		return best
	end

	-- ------------------------------------------------------------ comportement
	function ENT:RunBehaviour()
		while true do
			local target = self:FindTarget()
			if IsValid(target) then
				self:ChaseAndAttack(target)
			elseif self.JMoveGoal then
				local goal = self.JMoveGoal
				self.JMoveGoal = nil
				self:StartActivity(ACT_WALK)
				self.loco:SetDesiredSpeed(self.JSpeed)
				self:MoveToPos(goal, { tolerance = 60, maxage = 8, repath = 2 })
				self:StartActivity(ACT_IDLE)
				self.JHoldUntil = CurTime() + 15 -- reste sur place un moment avant de revenir au maitre
			elseif IsValid(self.JOwner) and (self.JHoldUntil or 0) < CurTime() and self:GetPos():DistToSqr(self.JOwner:GetPos()) > 350 * 350 then
				self:FollowOwner()
			else
				if self:GetActivity() ~= ACT_IDLE then self:StartActivity(ACT_IDLE) end
				if CurTime() > self.NextGrowl then
					self.NextGrowl = CurTime() + math.Rand(8, 16)
					self:EmitSound(GROWLS[math.random(#GROWLS)], 75, math.random(60, 80))
				end
				coroutine.wait(0.4)
			end
			coroutine.yield()
		end
	end

	function ENT:FollowOwner()
		local owner = self.JOwner
		local offset = Vector(math.Rand(-1, 1), math.Rand(-1, 1), 0):GetNormalized() * 200
		self:StartActivity(ACT_WALK)
		self.loco:SetDesiredSpeed(self.JSpeed * 1.4)
		self:MoveToPos(owner:GetPos() + offset, { tolerance = 120, maxage = 3, repath = 1 })
		self:StartActivity(ACT_IDLE)
	end

	function ENT:FaceTarget(target, steps)
		for i = 1, steps do
			if not IsValid(target) then return end
			self.loco:FaceTowards(target:GetPos())
			coroutine.yield()
		end
	end

	function ENT:ChaseAndAttack(target)
		local path = Path("Follow")
		path:SetMinLookAheadDistance(300)
		path:SetGoalTolerance(self.JMinRange)
		path:Compute(self, target:GetPos())
		self:StartActivity(ACT_WALK)
		self.loco:SetDesiredSpeed(self.JSpeed)
		while IsValid(target) and self:IsValidTarget(target) do
			local dist = self:GetPos():Distance(target:GetPos())
			local canSee = self:Visible(target)
			if canSee and dist < self.JRange and CurTime() > self.NextJutsu then
				self:DoAttack(target, dist < self.JMinRange * 1.6)
				path:Compute(self, target:GetPos())
				self:StartActivity(ACT_WALK)
			elseif dist > self.JMinRange then
				if path:GetAge() > 0.4 then path:Compute(self, target:GetPos()) end
				path:Update(self)
			else
				-- au contact : on attend le prochain coup en faisant face a la cible
				if self:GetActivity() ~= ACT_IDLE then self:StartActivity(ACT_IDLE) end
				self.loco:FaceTowards(target:GetPos())
			end
			if dist > self.JMinRange and self:GetActivity() ~= ACT_WALK then self:StartActivity(ACT_WALK) end
			if self.loco:IsStuck() then
				self:HandleStuck()
				return
			end
			if dist > self.JSightRange * 1.3 then break end
			coroutine.yield()
		end
		self.JEnemy = nil
		self:StartActivity(ACT_IDLE)
	end

	function ENT:MaskPos()
		-- point d'attache "mouth" defini dans le .qc (au centre du masque)
		local id = self:LookupAttachment("mouth")
		if id and id > 0 then
			local att = self:GetAttachment(id)
			if att then return att.Pos + self:GetForward() * 10 end
		end
		local s = self:GetModelScale()
		return self:GetPos() + self:GetForward() * 30 * s + Vector(0, 0, self.JMaskHeight * s)
	end

	function ENT:DoAttack(target, melee)
		self:FaceTarget(target, 12)
		if not IsValid(target) then return end
		self.NextJutsu = CurTime() + self.JCooldown * math.Rand(0.85, 1.25)
		local seq = melee and "attack_melee" or "attack"
		local delay = melee and self.JImpactDelay * 0.75 or self.JImpactDelay
		timer.Simple(delay, function()
			if not IsValid(self) or not IsValid(target) then return end
			if melee then
				self:ClawHit(target)
			else
				self:FireJutsu(target)
			end
		end)
		self:PlaySequenceAndWait(seq, 1)
	end

	function ENT:Damage(ent, amount, dtype, force)
		local d = DamageInfo()
		local owner = IsValid(self.JOwner) and self.JOwner or self
		d:SetDamage(amount * GetConVar("jiongu_damage_scale"):GetFloat())
		d:SetDamageType(dtype)
		d:SetAttacker(owner)
		d:SetInflictor(self)
		d:SetDamageForce(force or vector_origin)
		d:SetDamagePosition(ent:WorldSpaceCenter())
		ent:TakeDamageInfo(d)
	end

	function ENT:ClawHit(target)
		if self:GetPos():Distance(target:GetPos()) > self.JMinRange * 2.2 then return end
		local dir = (target:GetPos() - self:GetPos()):GetNormalized()
		self:Damage(target, 35, DMG_SLASH, dir * 12000)
		if target:IsPlayer() then target:SetVelocity(dir * 350 + Vector(0, 0, 180)) end
		self:EmitSound("npc/zombie/claw_strike" .. math.random(1, 3) .. ".wav", 80, 80)
	end

	-- chaque element surcharge cette fonction
	function ENT:FireJutsu(target)
	end

	-- ------------------------------------------------------------ degats / mort
	function ENT:OnInjured(dmg)
		-- le coeur s'epuise : le masque se fissure (skin 1 du modele)
		if self:GetSkin() == 0 and self:Health() - dmg:GetDamage() < self:GetMaxHealth() * 0.35 then
			self:SetSkin(1)
			self:EmitSound("physics/concrete/concrete_break" .. math.random(2, 3) .. ".wav", 85, 110)
		end
		local att = dmg:GetAttacker()
		if IsValid(att) and att ~= self and not self:IsFriend(att) then
			self:SetJionguEnemy(att)
		end
	end

	function ENT:OnKilled(dmg)
		hook.Call("OnNPCKilled", GAMEMODE, self, dmg:GetAttacker(), dmg:GetInflictor())
		local ed = EffectData()
		ed:SetOrigin(self:GetPos() + Vector(0, 0, 40))
		ed:SetScale(3)
		util.Effect("ThumperDust", ed, true, true)
		self:EmitSound("npc/antlion_guard/antlion_guard_die" .. math.random(1, 2) .. ".wav", 90, 70)
		if IsValid(self.JOwner) and self.JOwner.JionguMonsters then
			self.JOwner.JionguMonsters[self.JElement] = nil
			self.JOwner:ChatPrint("[Jiongu] Un de tes coeurs a ete detruit : " .. self.PrintName)
		end
		-- la masse de fils s'effondre : pas de ragdoll (le modele n'a qu'un corps physique)
		for i = 1, 3 do
			local e2 = EffectData()
			e2:SetOrigin(self:GetPos() + Vector(math.Rand(-40, 40), math.Rand(-40, 40), 20 + i * 30))
			e2:SetScale(2)
			util.Effect("ThumperDust", e2, true, true)
		end
		self:SetNoDraw(true)
		self:SetNotSolid(true)
		timer.Simple(0, function() if IsValid(self) then self:Remove() end end)
	end

	function ENT:OnRemove()
		if IsValid(self.JOwner) and self.JOwner.JionguMonsters and self.JOwner.JionguMonsters[self.JElement] == self then
			self.JOwner.JionguMonsters[self.JElement] = nil
		end
	end
end
