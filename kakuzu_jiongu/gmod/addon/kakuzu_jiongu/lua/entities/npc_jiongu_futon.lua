-- Masque du Vent : Futon - Atsugai (souffle d'air comprime, large zone devant le masque)
AddCSLuaFile()

ENT.Base = "npc_jiongu_base"
ENT.Type = "nextbot"
ENT.PrintName = "Jiongu - Masque du Vent (Futon)"
ENT.Spawnable = false

ENT.JModel = "models/kakuzu_jiongu/jiongu_futon.mdl"
ENT.JElement = "futon"
ENT.JHealth = 700
ENT.JSpeed = 170
ENT.JRange = 800
ENT.JCooldown = 4.5
ENT.JMaskHeight = 36
ENT.JHull = 46
ENT.JHullHeight = 70

if SERVER then
	function ENT:FireJutsu(target)
		local start = self:MaskPos()
		local dir = (target:WorldSpaceCenter() - start):GetNormalized()
		local range = 850
		local cosCone = math.cos(math.rad(32))
		local ed = EffectData()
		ed:SetOrigin(start)
		ed:SetNormal(dir)
		ed:SetMagnitude(range)
		util.Effect("jiongu_wind", ed, true, true)
		self:EmitSound("ambient/wind/windgust.wav", 95, 70)
		self:EmitSound("weapons/physcannon/energy_sing_explosion2.wav", 90, 60)
		for _, ent in ipairs(ents.FindInSphere(start, range)) do
			if IsValid(ent) and ent ~= self and not self:IsFriend(ent) then
				local to = ent:WorldSpaceCenter() - start
				local d = to:Length()
				if d > 1 and to:GetNormalized():Dot(dir) > cosCone then
					local falloff = 1 - math.Clamp(d / range, 0, 1) * 0.6
					local push = dir * 1100 * falloff + Vector(0, 0, 260)
					if ent:IsPlayer() or ent:IsNPC() or ent:IsNextBot() then
						self:Damage(ent, 55 * falloff, DMG_BLAST, push * 40)
						if ent:IsPlayer() then
							ent:SetVelocity(push)
						elseif ent:IsNextBot() and ent.loco then
							ent.loco:Jump()
							ent.loco:SetVelocity(push)
						end
					else
						local phys = ent:GetPhysicsObject()
						if IsValid(phys) then phys:ApplyForceCenter(push * phys:GetMass() * 1.2) end
					end
				end
			end
		end
	end
end
