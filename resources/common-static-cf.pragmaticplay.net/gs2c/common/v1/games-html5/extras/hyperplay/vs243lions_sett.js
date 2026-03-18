var hp_waitForFSOptions = true;

HPVARS.FSBGPickIndex = Vars.PickedItemIndexLocal_FSBGPick;
HPVARS.FSBGPickEvent = Vars.Evt_DataToCode_ItemPickedFSBGPick;

var getFSRevealedLabel = function(pickableOption) {
	var labels = pickableOption.GetComponentsInChildren(UILabel, true);
	var fsTXT = pickableOption.freeSpinsCountLabels[0].text;
	var text = fsTXT + " " + labels[1].text;
	if (pickableOption.freeSpinsMultiplierLabels != undefined && pickableOption.freeSpinsMultiplierLabels.length > 0) {
		var multiplierTXT = pickableOption.freeSpinsMultiplierLabels[0].text;
		text = text + " - " + labels[2].text + " " + multiplierTXT;
	}

	return text;
}

var getFSLabelText = function(pickableOption, isMystery) {

	var text;
	var labels = pickableOption.GetComponentsInChildren(UILabel, true);
	if (isMystery) {
		text = labels[4].text + " " + labels[5].text + " - " + labels[6].text + " " + labels[7].text;
	} else {
		var fsTXT = pickableOption.freeSpinsCountLabels[0].text;
		text = fsTXT + " " + labels[1].text;
		if (pickableOption.freeSpinsMultiplierLabels != undefined && pickableOption.freeSpinsMultiplierLabels.length > 0) {
			var multiplierTXT = pickableOption.freeSpinsMultiplierLabels[0].text;
			text = text + " - " + labels[2].text + " " + multiplierTXT;
		}
	}

	return text;
}

hyperTexts.specialFeatureText = hyperTexts.specialFeatureText2;
hyperTexts.selectFeatureText = hyperTexts.selectFeatureText2;

