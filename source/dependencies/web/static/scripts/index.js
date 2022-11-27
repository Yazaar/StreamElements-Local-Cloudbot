let s = io.connect(window.location.origin)

let ResetExtensionBtnActive = false
let ResetExtensionBtn = document.querySelector('#ResetExtensions')

let selectedPlatform = null
let currentTMI = null
let generateTMITimeout = null

let newRegularAliasTextField = document.getElementById('RegularInput')
let newRegularIDTextField = document.getElementById('RegularIdInput')
let newRegularGroupNameField = document.getElementById('RegularGroupInput')

let saveTwitchInstanceBTN = document.getElementById('SaveTwitch')
let currentTwitchInstanceAliasElement = document.getElementById('NewTwitchAlias')
let currentTMIElement = document.getElementById('GeneratedTMI')
let currentTMIAccountNameElement = document.querySelector('#TMIAccountName span')
let twitchBotsSelector = document.getElementById('SelectedTwitch')
let twitchInstanceDataBlock = document.getElementById('TwitchInstanceData')
let twitchInstanceCategory = document.getElementById('TwitchInstanceCategory')
let twitchConfigItemInput = document.getElementById('TwitchConfigItemInput')
let twitchConfigs = document.getElementById('TwitchInstanceConfigs')
let twitchCurrentRegularGroups = document.getElementById('TwitchCurrentRegularGroups')
let twitchCurrentChannels = document.getElementById('TwitchCurrentChannels')

let saveStreamElementsBTN = document.getElementById('SaveStreamElements')
let selectedStreamElements = document.getElementById('SelectedStreamElements')
let newStreamElementsAlias = document.getElementById('NewStreamElementsAlias')
let generatedJWT = document.getElementById('GeneratedJWT')
let currentJWTAccountNameElement = document.querySelector('#JTWAccountName span')
let streamElementsInstanceDataBlock = document.getElementById('StreamElementsInstanceData')
let discordCurrentRegularGroups = document.getElementById('DiscordCurrentRegularGroups')
let currentJWT = null
let validateJWTTimeout = null

let saveDiscordBTN = document.getElementById('SaveDiscord')
let selectedDiscord = document.getElementById('SelectedDiscord')
let discordInstanceDataBlock = document.getElementById('DiscordInstanceData')
let newDiscordAlias = document.getElementById('NewDiscordAlias')
let generatedToken = document.getElementById('GeneratedToken')
let currentTokenBotNameElement = document.querySelector('#TokenAccountName span')
let discordMembersIntent = document.getElementById('DiscordMembersIntent')
let discordPresencesIntent = document.getElementById('DiscordPresencesIntent')
let discordMessageContentIntent = document.getElementById('DiscordMessageContentIntent')
let currentToken = null
let validateTokenTimeout = null

let manageRegularGroup = document.getElementById('ManageRegularGroup')

let twitchRegularGroupList = document.getElementById('TwitchRegularGroupList')
let discordRegularGroupList = document.getElementById('DiscordRegularGroupList')

let regularList = document.getElementById('CurrentRegulars')
let searchTimeout = null

function voidFunc() {}

function createLog(title, message) {
    let new_element = document.createElement('div')
    let new_h2 = document.createElement('h2')
    let new_p = document.createElement('p')
    new_h2.innerText = title
    new_p.innerText = message
    new_element.appendChild(new_h2)
    new_element.appendChild(new_p)
    return new_element
}

function parseJSON(data) {
    try {
        return JSON.parse(data)
    } catch(e) {
        return null
    }
}

function setListeners() {
    let e = document.querySelectorAll('#settings .rangeNumber[data-settingTarget]')
    for (let i = 0; i < e.length; i++) {
        let subE = e[i]
        let eRange = document.querySelector('#settings input[type=range][data-settingname="' + e[i].getAttribute('data-settingTarget') + '"]')
        if (!eRange) continue
        subE.innerText = eRange.value;
        eRange.addEventListener('input', function() {
            subE.innerText = eRange.value;
        })
    }

    e = document.querySelectorAll('#settings input[type=number]')
    for (let i = 0; i < e.length; i++) {
        let subE = e[i]
        let prevV = subE.value
        let minV = parseFloat(subE.min)
        let maxV = parseFloat(subE.max)
        subE.addEventListener('input', function() {
            let newV = parseFloat(subE.value)
            if ((!isNaN(minV) && newV < minV) || (!isNaN(maxV) && newV > maxV)) subE.value = prevV
            else prevV = newV
        })
    }
}

function searchRegularGroup(regulargroup) {
    if (selectedPlatform === null) return
    s.emit('GetRegulars', {platform: selectedPlatform, group: regulargroup})
}

function validateTMI(tmi) {
    if (tmi.startsWith('oauth:')) tmi = tmi.substring(6)

    fetch('https://id.twitch.tv/oauth2/validate', {
        headers: {
            Authorization: 'Bearer ' + tmi
        }
    }).then(fetchdata => fetchdata.json())
    .then(tmiJSON => {
         if (tmiJSON.login === undefined) {
            currentTMIAccountNameElement.innerText = 'invalid :('
            return
        }
        currentTMI = 'oauth:' + tmi
        currentTMIAccountNameElement.innerText = tmiJSON.login
    })
}

function newTMI(tmi) {
    if (generateTMITimeout !== null) clearTimeout(generateTMITimeout)

    currentTMI = null
    if (tmi.length === 0) {
        currentTMIAccountNameElement.innerText = ''
        return
    }
    currentTMIAccountNameElement.innerText = 'loading...'
    generateTMITimeout = setTimeout(() => validateTMI(tmi), 2500)
}

function filterAlias(alias) {
    let aliasL = alias.toLowerCase()
    let users = document.querySelectorAll('#CurrentRegulars > .user');
    for (let u of users) {
        if (u.querySelector('.alias').innerText.toLowerCase().startsWith(aliasL)) {
            u.classList.remove('hidden')
        } else {
            u.classList.add('hidden')
            u.classList.remove('selected')
        }
    }
}

function finaliseDelete(triggerElement, onDeleteCallback) {
    onDeleteCallback(triggerElement)
    triggerElement.parentElement.removeChild(triggerElement)
}

function disposeDelete(triggerElement) {
    triggerElement.classList.remove('deletable')
    triggerElement.classList.remove('clicked')
}

function activateDelete(triggerElement) {
    triggerElement.classList.add('deletable')
    setTimeout(disposeDelete, 5000, triggerElement)
}

function triggerDelete(triggerElement, onDeleteCallback) {
    if (triggerElement.classList.contains('deletable')) {
        finaliseDelete(triggerElement, onDeleteCallback)
        return
    }
    
    if (triggerElement.classList.contains('clicked')) return
    
    triggerElement.classList.add('clicked')
    
    setTimeout(activateDelete, 1000, triggerElement)
}

function onRegularDelete(regularElement) {
    let regularID = regularElement.querySelector('.platformID')
    let groupname = newRegularGroupNameField.value
    
    if (regularID === null) return
    
    s.emit('DeleteRegular', {platform: selectedPlatform, userId: regularID.innerText, groupName: groupname})
}

function showRegular(regular) {
    let div = document.createElement('div')
    div.classList.add('user')
    div.setAttribute('data-platformID', regular.id)
    let alias = document.createElement('div')
    alias.classList.add('alias')
    alias.innerText = regular.alias
    let platformID = document.createElement('div')
    platformID.classList.add('platformID')
    platformID.innerText = regular.id
    div.appendChild(alias)
    div.appendChild(platformID)
    div.addEventListener('click', function(){ triggerDelete(this, onRegularDelete) })
    regularList.appendChild(div)
}

function addToGroupList(grouplist, regularGroup) {
    if (grouplist.querySelector('option[value="' + regularGroup + '"]') !== null) return
    let opt = document.createElement('option')
    opt.value = regularGroup
    opt.innerText = regularGroup
    grouplist.appendChild(opt)
}

function deleteFromGroupList(grouplist, regularGroup) {
    let match = grouplist.querySelector('option[value="' + regularGroup + '"]')
    if (match === null) return
    grouplist.removeChild(match)
}

function showTwitchRegularGroup(regularGroup) {
    addToGroupList(twitchRegularGroupList, regularGroup)

    let d = document.createElement('div')
    d.innerText = regularGroup
    d.classList.add('configItem')
    d.setAttribute('data-regulargroupname', regularGroup)
    twitchCurrentRegularGroups.appendChild(d)
}

function showDiscordRegularGroup(regularGroup) {
    addToGroupList(discordRegularGroupList, regularGroup)

    let d = document.createElement('div')
    d.innerText = regularGroup
    d.classList.add('configItem')
    d.setAttribute('data-regulargroupname', regularGroup)
    discordCurrentRegularGroups.appendChild(d)
}

function deleteTwitchRegularGroup(regularGroup) {
    deleteFromGroupList(twitchRegularGroupList, regularGroup)

    let d = twitchCurrentRegularGroups.querySelector('div[data-regulargroupname="' + regularGroup + '"]')
    if (d === null) return
    d.parentElement.removeChild(d)
}

function deleteDiscordRegularGroup(regularGroup) {
    deleteFromGroupList(discordRegularGroupList, regularGroup)

    let d = discordCurrentRegularGroups.querySelector('div[data-regulargroupname="' + regularGroup + '"]')
    if (d === null) return
    d.parentElement.removeChild(d)
}

function showTwitchInstance(twitch) {
    let opt = document.createElement('option')
    opt.selected = true
    opt.value = twitch.id
    opt.text = twitch.alias
    twitchBotsSelector.appendChild(opt)
    selectedTwitchInstance(twitch.id)
}

function selectedTwitchInstance(twitchID) {
    twitchInstanceDataBlock.classList.remove('hidden')
    twitchInstanceCategory.value = 'channels'
    twitchInstanceCategoryChanged()
    
    if (twitchID === 'NEW') {
        displayTwitchInstance('', '', [], [])
        return;
    }
    s.emit('GetTwitchInstanceConfigs', twitchID)
}

function twitchConfigAddChannel(channel) {
    if (channel.length === 0) return false
    let channelL = channel.toLowerCase()
    if (twitchCurrentChannels.querySelector('[data-channel="' + channelL + '"]') !== null) return false
    let d = document.createElement('div')
    d.innerText = channelL
    d.classList.add('configItem')
    d.setAttribute('data-channel', channelL)
    twitchCurrentChannels.appendChild(d)
    d.addEventListener('click', function() { triggerDelete(d, voidFunc) })
    return true
}

function twitchConfigRemoveChannel(channel) {
    console.log('remove channel', channel)
}

function displayTwitchInstance(alias, tmi, channels, regularGroups) {
    twitchCurrentChannels.innerHTML = ''
    currentTMIElement.value = tmi
    newTMI(tmi)
    currentTwitchInstanceAliasElement.value = alias
    for(let rg of twitchCurrentRegularGroups.children) {
        rg.classList.remove('selected')
    }
    
    channels.forEach((c) => {
        let d = document.createElement('div')
        d.className.add('configItem')
        d.setAttribute('data-channel', c)
        d.innerText = c
        twitchCurrentChannels.appendChild(d)
    });

    regularGroups.forEach((rg) => {
        let d = twitchCurrentRegularGroups.querySelector('div[data-regulargroupname="' + rg + '"]')
        d.classList.add('selected')
    });
}

function regularGroupNameInputChanged() {
    if (searchTimeout !== null) clearTimeout(searchTimeout)
    manageRegularGroup.classList.add('hidden')
    let v = this.value || ''
    if (v.length === 0) return
    searchTimeout = setTimeout(() => searchRegularGroup(v), 1000)
}

function bubbleToClass(container, clicked, classname) {
    while (!clicked.classList.contains(classname)) {
        if (clicked === container) return null
        clicked = clicked.parentElement
    }
    return clicked
}

function twitchInstanceCategoryChanged() {
    twitchConfigs.classList.remove(...twitchConfigs.classList)
    twitchConfigs.classList.add(twitchInstanceCategory.value)
}

function convertNodeList(nodeList, converter) {
    let res = []
    for (let e of nodeList) {
        res.push(converter(e))
    }
    return res
}

function getSelectedRegularGroups(e) {
    return convertNodeList(e.querySelectorAll('.configItem.selected'), x => x.getAttribute('data-regulargroupname'))
}

function getChannels(e) {
    return convertNodeList(e.querySelectorAll('.configItem'), x => x.getAttribute('data-channel'))
}

function selectedStreamElementsInstance(streamElementsID) {
    streamElementsInstanceDataBlock.classList.remove('hidden')
    if (streamElementsID === 'NEW') {
        displayStreamElementsInstance('', '')
        return;
    }
    s.emit('GetStreamElementsInstanceConfigs', streamElementsID)
}

function validateJWT(jwt) {
    fetch('https://api.streamelements.com/kappa/v2/users/current', {
        headers: {
            Authorization: 'Bearer ' + jwt
        }
    })
    .then(fetchdata => fetchdata.json())
    .then(jwtJSON => {
        if (jwtJSON.username === undefined) {
            currentJWTAccountNameElement.innerText = 'invalid :('
            return
        }
        currentJWT = jwt
        currentJWTAccountNameElement.innerText = jwtJSON.username
    })
}

function newJWT(jwt) {
    if (validateJWTTimeout !== null) clearTimeout(validateJWTTimeout)

    currentJWT = null
    if (jwt.length === 0) {
        currentJWTAccountNameElement.innerText = ''
        return
    }
    currentJWTAccountNameElement.innerText = 'loading...'
    validateJWTTimeout = setTimeout(() => validateJWT(jwt), 2500)
}

function displayStreamElementsInstance(alias, jwt) {
    newStreamElementsAlias.value = alias
    generatedJWT.value = jwt
    newJWT(jwt)
}

function selectedDiscordInstance(discordId) {
    discordInstanceDataBlock.classList.remove('hidden')
    if (discordId === 'NEW') {
        displayDiscordInstance('', '', [])
        return;
    }
    s.emit('GetDiscordInstanceConfigs', discordId)
}

function displayDiscordInstance(alias, token, regularGroups, membersIntent, presencesIntent, messageContentIntent) {
    newDiscordAlias.value = alias
    generatedToken.value = token
    discordMembersIntent.checked = membersIntent
    discordPresencesIntent.checked = presencesIntent
    discordMessageContentIntent.checked = messageContentIntent
    newToken(token)
}

function newToken(token) {
    if (validateTokenTimeout !== null) clearTimeout(validateTokenTimeout)

    currentToken = null
    if (token.length === 0) {
        currentTokenBotNameElement.innerText = ''
        return
    }
    currentTokenBotNameElement.innerText = 'loading...'
    validateTokenTimeout = setTimeout(() => validateToken(token), 2500)
}

function validateToken(token) {
    fetch('https://discord.com/api/users/@me', {
        headers: {
            Authorization: 'Bot ' + token
        }
    })
    .then(fetchdata => fetchdata.json())
    .then(data => {
        if (data.username === undefined) {
            currentTokenBotNameElement.innerText = 'invalid :('
            return
        }
        currentToken = token
        currentTokenBotNameElement.innerText = data.username
    })
}

setListeners();

setTimeout(function() {
    ResetExtensionBtnActive = true
    ResetExtensionBtn.style.display = ''
}, 1000)

document.getElementById('ResetExtensions').addEventListener('click', () => {
    if (ResetExtensionBtnActive) {
        ResetExtensionBtn.style.display = 'none'
        ResetExtensionBtnActive = false
        s.emit('ResetExtensions')
    }
})

for (let i of document.querySelectorAll('article#setup .saveSetupButton')) {
    i.addEventListener('click', function() {
        let e = document.querySelector('article#setup')
        if (e != null) {
            e.classList.add('WaitingForSave')
        }

        let obj = {}
        
        let node = this.parentNode.querySelector('input')

        switch (node.id) {
            case 'server_port-input':
                obj.server_port = parseInt(node.value)
                break
            case 'exec_per_second-input':
                obj.executions_per_second = parseFloat(node.value)
                break
            default:
                return
        }

        s.emit('UpdateSettings', obj)
    })
}

for (let i of document.querySelectorAll('.OpenCloseButton')) {
    i.addEventListener('click', function() {
        document.querySelector(this.getAttribute('data-target')).classList.toggle('ClosedSetting')
    })
}

for (let i of document.querySelectorAll('.save_settings')) {
    i.addEventListener('click', function() {
        let name = this.getAttribute('data-name')
        let index = parseInt(this.getAttribute('data-index'))
        let settings = {}
        for (let j of this.parentElement.querySelectorAll('section input, section select')) {
            let value
            if (j.type.toLowerCase() === 'checkbox') {
                value = j.checked
            } else {
                value = j.value
            }
            if (/^\d+$/.test(value)) {
                value = parseInt(value)
            } else if (/^\d+\.\d+$/.test(value)) {
                value = parseFloat(value)
            }
            settings[j.getAttribute('data-settingname')] = value
        }
        s.emit('SaveSettings', {name: name, index: index, settings: settings})
    })
}

for (let i of document.querySelectorAll('.SetDefaultSetting')) {
    i.addEventListener('click', function() {
        let value = i.getAttribute('data-default')
        let input = i.parentElement.querySelector('input, select')
        
        if (!input) return
        
        let typeLower = input.type.toLowerCase()
        if (typeLower === 'checkbox') {
            input.checked = value
        } else {
            input.value = value

            if (typeLower === 'range') {
                let rangeNum = document.querySelector('#settings p[data-settingTarget="' + input.getAttribute('data-settingname') + '"]')
                if (rangeNum) rangeNum.innerText = value
            }
        }
    })
}

for (let i of document.querySelectorAll('.ToggleExtension')) {
    i.addEventListener('click', function() {
        s.emit('ToggleExtension', {
            module: this.getAttribute('data-module'),
            active: this.checked
        })
    })
}

document.getElementById('ClearEvents').addEventListener('click', () => {
    document.querySelector('article#events section.data').innerHTML = ''
    s.emit('ClearEvents')
})

document.getElementById('ClearLogs').addEventListener('click', () => {
    document.querySelector('article#logs section.data').innerHTML = ''
    s.emit('ClearLogs')
})

document.getElementById('ClearMessages').addEventListener('click', () => {
    document.querySelector('article#messages section.data').innerHTML = ''
    s.emit('ClearMessages')
})

document.getElementById('RegularPlatforms').addEventListener('input', function() {
    selectedPlatform = this.value.toLowerCase();
    newRegularGroupNameField.value = ''
    regularGroupNameInputChanged()
    switch(selectedPlatform) {
        case 'twitch':
            newRegularGroupNameField.setAttribute('list', 'TwitchRegularGroupList')
            break
            case 'discord':
            newRegularGroupNameField.setAttribute('list', 'DiscordRegularGroupList')
            break
            default:
            newRegularGroupNameField.setAttribute('list', '')
    }
})

newRegularGroupNameField.addEventListener('input', regularGroupNameInputChanged);

document.getElementById('AddRegular').addEventListener('click', function() {
    let regularAlias = newRegularAliasTextField.value
    let regularID = newRegularIDTextField.value
    let regularGroupName = newRegularGroupNameField.value
    
    if (regularAlias.length === 0 || regularID.length === 0 || regularGroupName.length === 0 || selectedPlatform === null) return

    newRegularAliasTextField.value = ''
    newRegularIDTextField.value = ''

    s.emit('AddRegular', {alias: regularAlias, userId: regularID, groupName: regularGroupName, platform: selectedPlatform})
})

document.getElementById('SearchRegularAlias').addEventListener('input', function() { filterAlias(this.value) })

document.getElementById('TwitchAddConfigItem').addEventListener('click', function() {
    let v = twitchConfigItemInput.value
    if (twitchConfigAddChannel(v)) twitchConfigItemInput.value = ''
})

currentTMIElement.addEventListener('input', function() {
    newTMI(this.value)
})

twitchInstanceCategory.addEventListener('input', twitchInstanceCategoryChanged)

twitchCurrentRegularGroups.addEventListener('click', function(e) {
    let configItem = bubbleToClass(this, e.target, 'configItem')
    if (configItem === null) return
    configItem.classList.toggle('selected')
})

twitchBotsSelector.addEventListener('input', function() { selectedTwitchInstance(this.value) })

saveTwitchInstanceBTN.addEventListener('click', function() {
    if (this.classList.contains('disabled')) return

    let instanceID = twitchBotsSelector.value
    let instanceAlias = currentTwitchInstanceAliasElement.value
    let instanceTmi = currentTMI
    let instanceChannels = getChannels(twitchCurrentChannels)
    let instanceRegularGroups = getSelectedRegularGroups(twitchCurrentRegularGroups)

    if (instanceTmi === null || instanceAlias.length === 0) return

    this.classList.add('disabled')

    s.emit('SaveTwitchInstance', {
        id: instanceID,
        alias: instanceAlias,
        tmi: instanceTmi,
        channels: instanceChannels,
        regularGroups: instanceRegularGroups
    })
})

selectedStreamElements.addEventListener('input', function() { selectedStreamElementsInstance(this.value) })

generatedJWT.addEventListener('input', function() { newJWT(this.value) })

saveStreamElementsBTN.addEventListener('click', function() {
    if (this.classList.contains('disabled')) return

    let instanceID = selectedStreamElements.value
    let instanceAlias = newStreamElementsAlias.value
    let instanceJWT = currentJWT

    if (instanceJWT === null || instanceAlias.length === 0) return

    this.classList.add('disabled')

    s.emit('SaveStreamElementsInstance', {
        id: instanceID,
        alias: instanceAlias,
        jwt: instanceJWT
    })
})

selectedDiscord.addEventListener('input', function() { selectedDiscordInstance(this.value) })

generatedToken.addEventListener('input', function() { newToken(this.value) })

saveDiscordBTN.addEventListener('click', function() {
    if (this.classList.contains('disabled')) return

    let instanceID = selectedDiscord.value
    let instanceAlias = newDiscordAlias.value
    let instanceToken = currentToken
    let membersIntent = discordMembersIntent.checked
    let presencesIntent = discordPresencesIntent.checked
    let messageContentIntent = discordMessageContentIntent.checked
    let instanceRegularGroups = getSelectedRegularGroups(discordCurrentRegularGroups)
    
    if (instanceToken === null || instanceAlias.length === 0) return

    this.classList.add('disabled')

    s.emit('SaveDiscordInstance', {
        id: instanceID,
        alias: instanceAlias,
        token: instanceToken,
        regularGroups: instanceRegularGroups,
        membersIntent: membersIntent,
        presencesIntent: presencesIntent,
        messageContentIntent: messageContentIntent
    })
})

discordCurrentRegularGroups.addEventListener('click', function(e) {
    let configItem = bubbleToClass(this, e.target, 'configItem')
    if (configItem === null) return
    configItem.classList.toggle('selected')
})

s.on('SaveDiscordInstance', function(data) {
    saveDiscordBTN.classList.remove('disabled')
    if (data.success) {
        let e = selectedDiscord.querySelector('option[value="' + data.data.id + '"]')
        if (e) {
            e.innerText = data.data.alias
        } else {
            e = document.createElement('option')
            e.value = data.data.id
            e.innerText = data.data.alias
            e.selected = true
            selectedDiscord.appendChild(e)
        }
    }
})

s.on('SaveStreamElementsInstance', function(data) {
    saveStreamElementsBTN.classList.remove('disabled')
    if (data.success) {
        let e = selectedStreamElements.querySelector('option[value="' + data.data.id + '"]')
        if (e) {
            e.innerText = data.data.alias
        } else {
            e = document.createElement('option')
            e.value = data.data.id
            e.innerText = data.data.alias
            e.selected = true
            selectedStreamElements.appendChild(e)
        }
    }
})

s.on('SaveTwitchInstance', function(data) {
    saveTwitchInstanceBTN.classList.remove('disabled')
    if (data.success) {
        let e = twitchBotsSelector.querySelector('option[value="' + data.data.id + '"]')
        if (e) {
            e.innerText = data.data.alias
        } else {
            e = document.createElement('option')
            e.value = data.data.id
            e.innerText = data.data.alias
            e.selected = true
            twitchBotsSelector.appendChild(e)
        }
    }
})

s.on('GetTwitchInstanceConfigs', function(data) {
    if (twitchBotsSelector.value !== data.id) {
        displayTwitchInstance('', '', [], [])
        return
    }
    displayTwitchInstance(data.alias, data.tmi, data.channels, data.regularGroups)
})

s.on('GetStreamElementsInstanceConfigs', (data) => {
    if (selectedStreamElements.value !== data.id) {
        displayStreamElementsInstance('', '')
        return
    }
    displayStreamElementsInstance(data.alias, data.jwt)
})

s.on('GetDiscordInstanceConfigs', (data) => {
    if (selectedDiscord.value !== data.id) {
        displayDiscordInstance('', '', [], false, false, false)
        return
    }
    displayDiscordInstance(data.alias, data.token, data.regularGroups, data.membersIntent, data.presencesIntent, data.messageContentIntent)
})

s.on('AddRegular', function(data) {
    if (!data.success) return
    showRegular({alias: data.data.alias, id: data.data.userId})
    if (data.createdGroup) {
        switch (data.data.platform) {
            case 'twitch':
                showTwitchRegularGroup(data.data.groupName)
                break
            case 'discord':
                showDiscordRegularGroup(data.data.groupName)
                break
        }
    }
})

s.on('DeleteRegular', function(data) {
    if (!data.success) return
    if (data.deletedGroup) {
        switch (data.data.platform) {
            case 'twitch':
                deleteTwitchRegularGroup(data.data.groupName)
                break
                case 'discord':
                deleteDiscordRegularGroup(data.data.groupName)
                break
        }
    }
})

s.on('UpdateSettings', () => {
    let e = document.querySelector('article#setup')
    if (e != null) {
        e.classList.remove('WaitingForSave')
    }
})

s.on('ResetExtensions', (message) => {
    window.location.reload()
})

s.on("message", (message) => {
    console.log(message)
})

s.on('log', (message) => {
    document.querySelector('article#logs section.data').appendChild(createLog(message.module, message.message))
    for (let i of document.querySelectorAll('section.ExtensionItem p')) {
        if (i.innerHTML === message.module) {
            i.parentNode.querySelector('input').checked = false
        }
    }
})

s.on('StreamElementsEvent', (data) => {
    if (document.querySelector('article#events section.data').childElementCount > 99) {
        document.querySelector('article#events section.data').removeChild(document.querySelector('article#events section.data').lastChild)
    }
    
    let wrap = document.createElement('div')
    let h2 = document.createElement('h2')
    let p = document.createElement('p')

    h2.innerText = data.type

    switch (data.type) {
        case 'tip':
            p.innerText = data.data.amount + ' ' + data.data.currency + ' => ' + data.data.username
            break
        case 'cheer':
            p.innerText = data.data.amount + ' bits => ' + data.data.username
            break
        case 'host':
            p.innerText = data.data.amount + ' host => ' + data.data.username
            break
        case 'raid':
            p.innerText = data.data.amount + ' raid => ' + data.data.username
            break/*
        case 'perk':
            p.innerText = event.item + ' => ' + data.data.username
            break
        case 'merch':
            p.innerText = 'test merchname => ' + data.data.username
            break*/
        case 'subscriber':
            switch (data.data.tier) {
                case 'prime':
                    p.innerText = 'prime'
                    break
                case '2000':
                    p.innerText = 'tier 2'
                    break
                case '3000':
                    p.innerText = 'tier 3'
                    break
                default:
                    p.innerText = 'tier 1'
                    break
            }
            /*if (event.bulkGifted) {
                p.innerText += ' community gift => ' + event.sender + ' x' + event.amount
            } else */if (data.data.gifted) {
                p.innerText += ' gift => ' + data.data.sender + ' to ' + data.data.username
            } else {
                p.innerText += ', ' + data.data.amount + ' months => ' + data.data.username
            }
            break
        default:
            p.innerText = data.data.username
            break
    }
    
    wrap.appendChild(h2)
    wrap.appendChild(p)
    
    let e = document.querySelector('article#events section.data')
    e.insertBefore(wrap, e.firstChild)
})

s.on('StreamElementsTestEvent', (data) => {
    if (!data.listener.includes('latest')) {
        return
    }

    if (document.querySelector('article#events section.data').childElementCount > 99) {
        document.querySelector('article#events section.data').removeChild(document.querySelector('article#events section.data').lastChild)
    }

    let wrap = document.createElement('div')
    let h2 = document.createElement('h2')
    let p = document.createElement('p')

    let event = data.event

    if (event.type === 'perk') {
        h2.innerText = 'item redemption'
    } else {
        h2.innerText = event.type
    }

    if (event.isTest) {
        h2.innerText += ' (test)'
    }

    switch (event.type) {
        case 'follower':
            p.innerText = event.name
            break
        case 'tip':
            p.innerText = event.amount + ' TC => ' + event.name
            break
        case 'cheer':
            p.innerText = event.amount + ' bits => ' + event.name
            break
        case 'host':
            p.innerText = event.amount + ' viwers => ' + event.name
            break
        case 'raid':
            p.innerText = event.amount + ' viwers => ' + event.name
            break
        case 'perk':
            p.innerText = event.item + ' => ' + event.name
            break
        case 'merch':
            p.innerText = 'test merchname => ' + event.name
            break
        case 'subscriber':
            switch (event.tier) {
                case 'prime':
                    p.innerText = 'prime'
                    break
                case '2000':
                    p.innerText = 'tier 2'
                    break
                case '3000':
                    p.innerText = 'tier 3'
                    break
                default:
                    p.innerText = 'tier 1'
                    break
            }
            if (event.bulkGifted) {
                p.innerText += ' community gift => ' + event.sender + ' x' + event.amount
            } else if (event.gifted) {
                p.innerText += ' gift => ' + event.sender + ' to ' + event.name
            } else {
                p.innerText += ', ' + event.amount + ' months => ' + event.name
            }
            break
    }

    wrap.appendChild(h2)
    wrap.appendChild(p)

    let e = document.querySelector('article#events section.data')
    e.insertBefore(wrap, e.firstChild)
})

s.on('ToggleExtension', (message) => {
    let data = parseJSON(message)

    if (data === null) { return }
    if (data.success === false) {
        for (let i of document.querySelectorAll('.ToggleExtension')) {
            if (i.getAttribute('data-module') === data.module) {
                i.checked = message.active
            }
        }
    }
})

s.on('TwitchMessage', (message) => {
    if (document.querySelector('article#messages section.data').childElementCount > 99) {
        document.querySelector('article#messages section.data').removeChild(document.querySelector('article#messages section.data').firstElementChild)
    }
    let new_element = document.createElement('p')
    new_element.innerText = message.name + ': ' + message.message
    new_element.classList.add('message')
    document.querySelector('article#messages section.data').appendChild(new_element)
})

s.on('GetRegulars', (data) => {
    regularList.innerHTML = ''
    manageRegularGroup.classList.remove('hidden')
    if (!data.success) return
    data.regulars.forEach(regular => showRegular(regular))
});
