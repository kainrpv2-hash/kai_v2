-- Projectile du Suiton : bulle d'eau sous pression
AddCSLuaFile()

ENT.Type = "anim"
ENT.Base = "base_anim"
ENT.PrintName = "Suiton : Bulle d'eau"
ENT.Spawnable = false
ENT.RenderGroup = RENDERGROUP_TRANSLUCENT

function ENT:Initialize()
	if SERVER then
		self:SetModel("models/hunter/misc/sphere025x025.mdl")
		self:PhysicsInitSphere(10, "default_silent")
		self:SetCollisionGroup(COLLISION_GROUP_PROJECTILE)
		self:DrawShadow(false)
		local phys = self:GetPhysicsObject()
		if IsValid(phys) then
			phys:EnableGravity(false)
			phys:EnableDrag(false)
			phys:SetMass(5)
			phys:Wake()
		end
		self.DieTime = CurTime() + 3
		util.SpriteTrail(self, 0, Color(120, 180, 255, 200), true, 34, 0, 0.3, 1 / 34 * 0.5, "trails/smoke")
	end
end

if SERVER then
	function ENT:Launch(vel)
		local phys = self:GetPhysicsObject()
		if IsValid(phys) then phys:SetVelocity(vel) end
	end

	function ENT:Think()
		if self.PendingHit then
			self:Burst(self.PendingHit, self.PendingNormal)
		elseif CurTime() > self.DieTime then
			self:Burst(self:GetPos(), vector_up)
		end
		self:NextThink(CurTime() + 0.05)
		return true
	end

	-- l'impact est traite au prochain Think (pas d'entite creee dans le callback physique)
	function ENT:PhysicsCollide(data)
		if self.PendingHit or (IsValid(data.HitEntity) and data.HitEntity == self.JMonster) then return end
		self.PendingHit = data.HitPos
		self.PendingNormal = -data.HitNormal
		self:NextThink(CurTime())
	end

	function ENT:Burst(pos, normal)
		if self.Burst_done then return end
		self.Burst_done = true
		local attacker = IsValid(self.JAttacker) and self.JAttacker or self
		local scale = GetConVar("jiongu_damage_scale"):GetFloat()
		local ed = EffectData()
		ed:SetOrigin(pos)
		ed:SetNormal(normal)
		ed:SetScale(30)
		ed:SetFlags(0)
		util.Effect("watersplash", ed, true, true)
		local ed2 = EffectData()
		ed2:SetOrigin(pos)
		ed2:SetScale(2)
		util.Effect("WaterSurfaceExplosion", ed2, true, true)
		sound.Play("ambient/water/water_splash" .. math.random(1, 3) .. ".wav", pos, 90, 90)
		for _, ent in ipairs(ents.FindInSphere(pos, 180)) do
			if IsValid(ent) and ent ~= self.JMonster and ent ~= self.JAttacker then
				if ent:IsOnFire() then ent:Extinguish() end
				if ent:IsPlayer() or ent:IsNPC() or ent:IsNextBot() then
					local dir = (ent:WorldSpaceCenter() - pos):GetNormalized()
					local d = DamageInfo()
					d:SetDamage(45 * scale)
					d:SetDamageType(DMG_CRUSH)
					d:SetAttacker(attacker)
					d:SetInflictor(self)
					d:SetDamageForce(dir * 9000)
					ent:TakeDamageInfo(d)
					if ent:IsPlayer() then ent:SetVelocity(dir * 600 + Vector(0, 0, 200)) end
				end
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
		render.SetMaterial(glow)
		local p = self:GetPos()
		render.DrawSprite(p, 70, 70, Color(90, 160, 255, 220))
		render.DrawSprite(p, 30, 30, Color(220, 240, 255, 255))
	end
end
