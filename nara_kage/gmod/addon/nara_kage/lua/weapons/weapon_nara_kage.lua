-- Kagemane no Jutsu (clan Nara) : manipulation des ombres
--   Clic gauche : genou a terre, sceau, puis l'ombre part (camera dans sa pointe)
--   Clic droit  : annule / relache l'ombre
AddCSLuaFile()

SWEP.PrintName = "Kagemane no Jutsu"
SWEP.Author = "Nara Kage pack"
SWEP.Category = "Naruto - Clan Nara"
SWEP.Instructions = "Clic gauche : lancer l'ombre | Souris : la diriger | Clic droit : annuler / relacher"
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

function SWEP:PrimaryAttack()
	self:SetNextPrimaryFire(CurTime() + 0.6)
	if SERVER then NARA.Start(self:GetOwner()) end
end

function SWEP:SecondaryAttack()
	self:SetNextSecondaryFire(CurTime() + 0.4)
	if SERVER then NARA.Cancel(self:GetOwner()) end
end

function SWEP:Reload() end

function SWEP:Holster()
	if SERVER and IsValid(self:GetOwner()) then NARA.Cancel(self:GetOwner()) end
	return true
end

function SWEP:OnRemove()
	if SERVER and IsValid(self:GetOwner()) and NARA.Casts[self:GetOwner()] then NARA.Cancel(self:GetOwner()) end
end

function SWEP:DrawHUD()
	if NARA.Casts[self:GetOwner()] then return end
	draw.SimpleTextOutlined("Kagemane no Jutsu", "DermaLarge", ScrW() / 2, ScrH() - 140,
		Color(235, 230, 220), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER, 2, Color(0, 0, 0, 200))
	draw.SimpleTextOutlined("Clic gauche : lancer l'ombre    Clic droit : annuler", "DermaDefault",
		ScrW() / 2, ScrH() - 110, Color(200, 195, 185), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER, 1, Color(0, 0, 0, 200))
end
