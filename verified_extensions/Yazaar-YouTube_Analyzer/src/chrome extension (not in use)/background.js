chrome.tabs.onUpdated.addListener(function (tabId, changeInfo, tab) {
    if (changeInfo.status == 'complete' && /www\.youtube\.com\/watch/.test(tab.url)) {
        chrome.tabs.executeScript(tabId, {
            code: 'if(typeof(CurrentTabID) === \'undefined\'){var CurrentTabID = ' + tabId + '}else{CurrentTabID = ' + tabId +  '}'
        });
        chrome.tabs.executeScript(tabId, {
            file: 'inject.js'
        });
    }
})