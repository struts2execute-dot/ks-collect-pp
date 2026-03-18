var fsbgResponseScriptName = "ResponseHandler_BBS";
HPVARS.FSBGLabelsFromPaytable = true;
HPVARS.callFinalizeDisplayedWin = true;
HPVARS.lastTumbleIsZero = false;

var bonusMsgRootPath = "UI Root/XTRoot/Root/"
var symbol = UHT_GAME_CONFIG.GAME_SYMBOL;
var cvIdx = symbol.indexOf("_cv");
if (cvIdx != -1) {
	symbol = symbol.substr(0, cvIdx);
}

var bonusMsgLabels = {
	"fs": "LabelHolder5/Label5",
	"l2": "LabelHolder4/Label4",
	"md": "LabelHolder3/Label3",
	"mf": "LabelHolder1/Label1",
	"mm": "LabelHolder2/Label2",
}

if(Globals.isMobile) {
	if(symbol == "vs10dgold88")
		bonusMsgRootPath = bonusMsgRootPath + "Paytable_mobile/Paytable_portrait/Page4/Content/RealContent/FreeSpinsHolder1/RulesHolder/ListHolder3/";
	else if (symbol == "vs10fdsnake")
	{
		bonusMsgRootPath = bonusMsgRootPath + "Paytable_mobile/Paytable_portrait/Page4/Content/RealContent/FreeSpinsHolder1/RulesHolder/ListHolder3/";
		bonusMsgLabels["md"] = "LabelHolder3NEW/Label3";
		bonusMsgLabels["mf"] = "LabelHolder1NEW/Label1";
		bonusMsgLabels["mm"] = "LabelHolder2NEW/Label2";
	}
	else
		bonusMsgRootPath = bonusMsgRootPath + "Paytable_mobile/Paytable_portrait/Page4/Content/RealContent/FreeSpinsHolder2/ListHolder3/";
}
else {
	bonusMsgRootPath = bonusMsgRootPath + "Paytable/Pages/Page2/FreeSpinsHolder1/RulesHolder/ListHolder3/";

	if (symbol == "vs10fdsnake") {
		bonusMsgLabels["md"] = "LabelHolder3/Label3New";
		bonusMsgLabels["mf"] = "LabelHolder1/Label1New";
		bonusMsgLabels["mm"] = "LabelHolder2/Label2New";
	}
}
