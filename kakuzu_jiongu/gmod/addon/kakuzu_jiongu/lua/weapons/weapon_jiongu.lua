-- Jiongu (Kakuzu) : invoque et commande les quatre monstres masques
--   Clic gauche : fait sortir le prochain coeur (Feu > Vent > Foudre > Eau) la ou tu vises
--   Clic droit  : les monstres attaquent ce que tu vises (ou s'y deplacent si tu vises le sol)
--   Recharger   : les monstres retournent dans ton corps (disparaissent)
AddCSLuaFile()

SWEP.PrintName = "Jiongu (Kakuzu)"
SWEP.Author = "Kakuzu Jiongu pack"
SWEP.Category = "Naruto - Kakuzu (Jiongu)"
SWEP.Instructions = "Clic gauche : invoquer un coeur | Clic droit : attaquer la cible visee | R : rappeler"
SWEP.Spawnable = true
SWEP.AdminOnly = false
SWEP.Slot = 4
SWEP.SlotPos = 2
SWEP.DrawAmmo = false
SWEP.DrawCrosshair = true
SWEP.UseHands = false
SWEP.ViewModel = "models/weapons/c_arms.mdl"
SWEP.WorldModel = ""
SWEP.HoldType = "magic"

SWEP.Primary.ClipSize = -1
SWEP.Primary.DefaultClip = -1
SWEP.Primary.Automatic = false
SWEP.Primary.Ammo = "none"
SWEP.Secondary.ClipSize = -1
SWEP.Secondary.DefaultClip = -1
SWEP.Secondary.Automatic = false
SWEP.Secondary.Ammo = "none"

local ORDER = {
	{ el = "katon",  class = "npc_jiongu_katon",  name = "Masque du Feu" },
	{ el = "futon",  class = "npc_jiongu_futon",  name = "Masque du Vent" },
	{ el = "raiton", class = "npc_jiongu_raiton", name = "Masque de la Foudre" },
	{ el = "suiton", class = "npc_jiongu_suiton", name = "Masque de l'Eau" },
}

function SWEP:Initialize()
	self:SetHoldType(self.HoldType)
end

function SWEP:SetupDataTables()
	self:NetworkVar("Int", 0, "NextIndex")
end

function SWEP:NextFree(ply)
	local mons = ply.JionguMonsters or {}
	for k = 0, #ORDER - 1 do
		local idx = ((self:GetNextIndex() + k) % #ORDER) + 1
		if not IsValid(mons[ORDER[idx].el]) then return idx end
	end
	return nil
end

function SWEP:PrimaryAttack()
	self:SetNextPrimaryFire(CurTime() + 1.5)
	if CLIENT then return end
	local ply = self:GetOwner()
	if not IsValid(ply) then return end
	ply.JionguMonsters = ply.JionguMonsters or {}
	local idx = self:NextFree(ply)
	if not idx then
		ply:ChatPrint("[Jiongu] Tes quatre coeurs sont deja dehors.")
		return
	end
	local info = ORDER[idx]
	local tr = util.TraceLine({ start = ply:EyePos(), endpos = ply:EyePos() + ply:GetAimVector() * 500, filter = ply })
	local pos = tr.HitPos + tr.HitNormal * 10
	local down = util.TraceLine({ start = pos + Vector(0, 0, 40), endpos = pos - Vector(0, 0, 400), mask = MASK_SOLID_BRUSHONLY })
	pos = down.HitPos + Vector(0, 0, 4)
	local mon = ents.Create(info.class)
	if not IsValid(mon) then return end
	mon:SetPos(pos)
	mon:SetAngles(Angle(0, ply:EyeAngles().y, 0))
	mon.JOwner = ply
	mon:SetCreator(ply)
	mon:Spawn()
	mon:Activate()
	mon:SetJOwnerPlayer(ply)
	ply.JionguMonsters[info.el] = mon
	self:SetNextIndex(idx % #ORDER)
	local ed = EffectData()
	ed:SetOrigin(pos + Vector(0, 0, 30))
	ed:SetScale(3)
	util.Effect("ThumperDust", ed, true, true)
	ply:EmitSound("npc/antlion_guard/angry" .. math.random(1, 3) .. ".wav", 80, 80)
	ply:ChatPrint("[Jiongu] " .. info.name .. " invoque.")
	undo.Create("Jiongu")
	undo.AddEntity(mon)
	undo.SetPlayer(ply)
	undo.SetCustomUndoText("Rappel : " .. info.name)
	undo.Finish()
end

function SWEP:SecondaryAttack()
	self:SetNextSecondaryFire(CurTime() + 0.6)
	if CLIENT then return end
	local ply = self:GetOwner()
	if not IsValid(ply) or not ply.JionguMonsters then return end
	local tr = ply:GetEyeTrace()
	local target = tr.Entity
	local count = 0
	for _, mon in pairs(ply.JionguMonsters) do
		if IsValid(mon) then
			if IsValid(target) and mon:IsValidTarget(target) then
				mon:SetJionguEnemy(target)
			else
				mon.JEnemy = nil
				mon.JMoveGoal = tr.HitPos
			end
			count = count + 1
		end
	end
	if count > 0 then
		ply:EmitSound("npc/antlion_guard/frustrated_growl" .. math.random(1, 3) .. ".wav", 75, 90)
	end
end

function SWEP:Reload()
	if CLIENT then return end
	if (self.NextReloadTime or 0) > CurTime() then return end
	self.NextReloadTime = CurTime() + 1
	local ply = self:GetOwner()
	if not IsValid(ply) or not ply.JionguMonsters then return end
	for el, mon in pairs(ply.JionguMonsters) do
		if IsValid(mon) then
			local ed = EffectData()
			ed:SetOrigin(mon:GetPos() + Vector(0, 0, 40))
			ed:SetScale(2)
			util.Effect("ThumperDust", ed, true, true)
			mon:Remove()
		end
		ply.JionguMonsters[el] = nil
	end
	ply:ChatPrint("[Jiongu] Les coeurs sont rentres dans ton corps.")
end

function SWEP:DrawHUD()
	local idx = (self:GetNextIndex() % #ORDER) + 1
	draw.SimpleTextOutlined("Prochain coeur : " .. ORDER[idx].name, "DermaLarge", ScrW() / 2, ScrH() - 140,
		Color(235, 225, 210), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER, 2, Color(0, 0, 0, 200))
	draw.SimpleTextOutlined("Clic gauche : invoquer   Clic droit : attaquer   R : rappeler", "DermaDefault",
		ScrW() / 2, ScrH() - 110, Color(200, 190, 180), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER, 1, Color(0, 0, 0, 200))
end
