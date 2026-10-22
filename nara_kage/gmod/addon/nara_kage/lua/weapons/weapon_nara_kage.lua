-- Hiden : manipulation des ombres (clan Nara)
--   Clic gauche : lance la technique choisie
--   Clic droit  : annule / relache l'ombre
--   R           : technique suivante
AddCSLuaFile()

SWEP.PrintName = "Hiden : Ombres (Nara)"
SWEP.Author = "Nara Kage pack"
SWEP.Category = "Naruto - Clan Nara"
SWEP.Instructions = "Clic gauche : lancer | Clic droit : annuler / relacher | R : technique suivante"
SWEP.Spawnable = true
SWEP.AdminOnly = false
SWEP.Slot = 4
SWEP.SlotPos = 3
SWEP.DrawAmmo = false
SWEP.DrawCrosshair = true
SWEP.UseHands = true
SWEP.ViewModel = "models/weapons/c_arms.mdl"
SWEP.WorldModel = ""
SWEP.HoldType = "normal"

SWEP.Primary.ClipSize = -1
SWEP.Primary.DefaultClip = -1
SWEP.Primary.Automatic = false
SWEP.Primary.Ammo = "none"
SWEP.Secondary.ClipSize = -1
SWEP.Secondary.DefaultClip = -1
SWEP.Secondary.Automatic = false
SWEP.Secondary.Ammo = "none"

function SWEP:Initialize()
	self:SetHoldType(self.HoldType)
end

function SWEP:SetupDataTables()
	self:NetworkVar("Int", 0, "Tech")
end

function SWEP:CurrentTech()
	return math.Clamp(self:GetTech(), 0, #NARA.Techniques - 1) + 1
end

function SWEP:PrimaryAttack()
	self:SetNextPrimaryFire(CurTime() + 0.6)
	if CLIENT then return end
	NARA.Start(self:GetOwner(), self:CurrentTech())
end

function SWEP:SecondaryAttack()
	self:SetNextSecondaryFire(CurTime() + 0.4)
	if CLIENT then return end
	NARA.Cancel(self:GetOwner())
end

function SWEP:Reload()
	if (self.NextSwitch or 0) > CurTime() then return end
	self.NextSwitch = CurTime() + 0.35
	if CLIENT then return end
	self:SetTech((self:GetTech() + 1) % #NARA.Techniques)
	local t = NARA.Techniques[self:CurrentTech()]
	self:GetOwner():ChatPrint("[Nara] " .. t.name .. " (" .. t.fr .. ")")
end

function SWEP:Holster()
	if SERVER and IsValid(self:GetOwner()) then NARA.Cancel(self:GetOwner()) end
	return true
end

function SWEP:OnRemove()
	if SERVER and IsValid(self:GetOwner()) and NARA.Casts[self:GetOwner()] then NARA.Cancel(self:GetOwner()) end
end

function SWEP:DrawHUD()
	local rec = NARA.Casts[self:GetOwner()]
	if rec and rec.phase ~= NARA.PH_NONE then return end
	local t = NARA.Techniques[self:CurrentTech()]
	draw.SimpleTextOutlined(t.name, "DermaLarge", ScrW() / 2, ScrH() - 140,
		Color(235, 230, 220), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER, 2, Color(0, 0, 0, 200))
	draw.SimpleTextOutlined(t.fr .. "    Clic gauche : lancer   Clic droit : annuler   R : technique suivante", "DermaDefault",
		ScrW() / 2, ScrH() - 110, Color(200, 195, 185), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER, 1, Color(0, 0, 0, 200))
end
