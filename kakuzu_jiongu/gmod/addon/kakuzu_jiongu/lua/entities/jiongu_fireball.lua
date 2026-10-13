-- Projectile du Katon : petite boule de feu qui explose en tempete de flammes au contact
AddCSLuaFile()

ENT.Type = "anim"
ENT.Base = "base_anim"
ENT.PrintName = "Katon : Zukokku"
ENT.Spawnable = false
ENT.RenderGroup = RENDERGROUP_TRANSLUCENT

function ENT:Initialize()
	if SERVER then
		self:SetModel("models/hunter/misc/sphere025x025.mdl")
		self:PhysicsInitSphere(8, "default_silent")
		self:SetCollisionGroup(COLLISION_GROUP_PROJECTILE)
		self:DrawShadow(false)
		local phys = self:GetPhysicsObject()
		if IsValid(phys) then
			phys:EnableGravity(false)
			phys:EnableDrag(false)
			phys:SetMass(5)
			phys:Wake()
		end
		self.DieTime = CurTime() + 4
		util.SpriteTrail(self, 0, Color(255, 140, 40), true, 40, 0, 0.35, 1 / 40 * 0.5, "trails/plasma")
		self:Ignite(10, 0)
	end
end

if SERVER then
	function ENT:Launch(vel)
		local phys = self:GetPhysicsObject()
		if IsValid(phys) then phys:SetVelocity(vel) end
	end

	function ENT:Think()
		if self.PendingHit then
			self:Explode(self.PendingHit)
		elseif CurTime() > self.DieTime then
			self:Explode(self:GetPos())
		end
		self:NextThink(CurTime() + 0.05)
		return true
	end

	-- pas de creation/suppression d'entite dans le callback physique : on note l'impact,
	-- l'explosion a lieu au prochain Think
	function ENT:PhysicsCollide(data)
		if self.PendingHit or (IsValid(data.HitEntity) and data.HitEntity == self.JMonster) then return end
		self.PendingHit = data.HitPos
		self:NextThink(CurTime())
	end

	function ENT:Explode(pos)
		if self.Exploded then return end
		self.Exploded = true
		local attacker = IsValid(self.JAttacker) and self.JAttacker or self
		local scale = GetConVar("jiongu_damage_scale"):GetFloat()
		local ed = EffectData()
		ed:SetOrigin(pos)
		ed:SetMagnitude(3)
		ed:SetScale(2)
		util.Effect("Explosion", ed, true, true)
		util.BlastDamage(self, attacker, pos, 300, 95 * scale)
		for _, ent in ipairs(ents.FindInSphere(pos, 320)) do
			if IsValid(ent) and ent ~= self.JMonster and ent ~= self.JAttacker and (ent:IsPlayer() or ent:IsNPC() or ent:IsNextBot()) then
				ent:Ignite(5, 0)
			end
		end
		-- la tempete de feu se propage au sol
		for i = 1, 7 do
			local ang = (i / 7) * math.pi * 2
			local p = pos + Vector(math.cos(ang), math.sin(ang), 0) * math.Rand(60, 220)
			local tr = util.TraceLine({ start = p + Vector(0, 0, 64), endpos = p - Vector(0, 0, 256), mask = MASK_SOLID_BRUSHONLY })
			local fire = ents.Create("env_fire")
			if IsValid(fire) then
				fire:SetPos(tr.HitPos)
				fire:SetKeyValue("health", "6")
				fire:SetKeyValue("firesize", tostring(math.random(90, 140)))
				fire:SetKeyValue("fireattack", "1")
				fire:SetKeyValue("damagescale", tostring(4 * scale))
				fire:SetKeyValue("spawnflags", "5") -- duree infinie + deja allume (supprime par Kill ci-dessous)
				fire:Spawn()
				fire:Fire("StartFire", "", 0)
				fire:Fire("Kill", "", 6 + math.Rand(0, 2))
			end
		end
		self:Remove()
	end
end

if CLIENT then
	local glow = Material("sprites/light_glow02_add")
	function ENT:Draw()
	end
	function ENT:DrawTranslucent()
		local p = self:GetPos()
		render.SetMaterial(glow)
		local t = CurTime() * 20
		render.DrawSprite(p, 90 + math.sin(t) * 10, 90 + math.sin(t) * 10, Color(255, 120, 30, 255))
		render.DrawSprite(p, 40, 40, Color(255, 230, 150, 255))
	end
end
