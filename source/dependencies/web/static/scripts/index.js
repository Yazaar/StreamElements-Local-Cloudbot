let selectedPlatform = null

let regularList = document.getElementById('CurrentRegulars')
let newRegularAliasTextField = document.getElementById('RegularInput')
let newRegularIDTextField = document.getElementById('RegularIdInput')
let newRegularGroupNameField = document.getElementById('RegularGroupInput')

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
        parsed = JSON.parse(data)
    } catch(e) {
        parsed = null
    }
    return parsed
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
        });
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

function finaliseDelete(regularElement) {
    let regularID = regularElement.querySelector('.platformID')
    let groupname = newRegularGroupNameField.value

    if (regularID === null) return

    s.emit('DeleteRegular', {platform: selectedPlatform, userId: regularID.innerText, groupName: groupname})
}

function disposeDelete(regularElement) {
    regularElement.classList.remove('deletable')
    regularElement.classList.remove('clicked')
}

function activateDelete(regularElement) {
    regularElement.classList.add('deletable')
    setTimeout(disposeDelete, 5000, regularElement)
}

function deleteRegular(regularElement) {
    if (regularElement.classList.contains('deletable')) {
        finaliseDelete(regularElement)
        return
    }

    if (regularElement.classList.contains('clicked')) return

    regularElement.classList.add('clicked')
    setTimeout(activateDelete, 1000, regularElement)
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
    div.addEventListener('click', function(){ deleteRegular(this) })
    regularList.appendChild(div)
}

setListeners();

let s = io.connect(window.location.origin)
let Waiting4Response = false
let ToggleQueue = []
let Waiting4Save = false

let ResetExtensionBtnActive = false

let ResetExtensionBtn = document.querySelector('#ResetExtensions')
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
        if (Waiting4Save) {
            return
        }

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
            case 'jwt-input':
                obj.jwt_token =  node.value
                break
            case 'user_id-input':
                obj.user_id =  node.value
                break
            case 'tmi-input':
                obj.tmi =  node.value
                break
            case 'tmi_username-input':
                obj.tmi_twitch_username =  node.value
                break
            case 'twitch_channel-input':
                obj.twitch_channel =  node.value
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
    s.emit('GetRegularGroups', selectedPlatform)
})

let searchTimeout = null;
document.getElementById("RegularGroupInput").addEventListener('input', function() {
    if (searchTimeout !== null) clearTimeout(searchTimeout)
    let v = this.value;
    searchTimeout = setTimeout(() => searchRegularGroup(v), 1000);
});

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

s.on('AddRegular', function(data) {
    if (!data.success) return
    showRegular({alias: data.data.alias, id: data.data.userId})
})

s.on('DeleteRegular', function(data) {
    if (!data.success) return
    let regularElement = document.querySelector('#CurrentRegulars > .user[data-platformID="' + data.data.userId + '"]')
    if (regularElement === null) return
    regularElement.parentElement.removeChild(regularElement)
})

s.on('UpdateSettings', () => {
    let e = document.querySelector('article#setup')
    if (e != null) {
        e.classList.remove('WaitingForSave')
    }
    
    Waiting4Save = false
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
    data = parseJSON(message)

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

let regularGroupList = document.getElementById('RegularGroupList')
s.on('GetRegularGroups', (data) => {
    if (!data.success) return
    regularGroupList.innerHTML = ''
    data.groups.forEach(g => {
        let opt = document.createElement('option');
        opt.value = g
        opt.text = g
        regularGroupList.appendChild(opt)
    })
})

s.on('GetRegulars', (data) => {
    regularList.innerHTML = ''
    if (!data.success) return
    data.regulars.forEach(regular => showRegular(regular))
});
